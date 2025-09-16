# configurator/views.py
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import requests
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import escape
from .forms import QuizForm, ParticipantForm,JobApplicationForm, keep_at_secure_filename,ContactForm
from .models import (
    Answer,
    ChoiceImpact,
    Item,
    ProductGroup,
    QuizSession,
    Page,ContactMessage, ERPSettings # <-- your admin-configured ERP settings
)
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from .careers_api import fetch_job_list, fetch_job_details, submit_applicant
from django.views import View
from django.contrib import messages




class GroupExploreView(View):
    """
    Lists all active items in the selected product group.
    """
    template_name = "configurator/explore.html"

    def get(self, request, slug):
        group = get_object_or_404(ProductGroup, slug=slug, is_active=True)
        items = (
            Item.objects.filter(group=group, is_active=True)
            .prefetch_related("images", "features", "specs", "documents")
            .order_by("name")
        )
        return render(request, self.template_name, {"group": group, "items": items})


class ItemDetailView(View):
    template_name = "configurator/item_detail.html"

    def get(self, request, item_id):
        item = get_object_or_404(
            Item.objects.prefetch_related("images", "features", "specs", "documents", "group"),
            pk=item_id, is_active=True
        )
        return render(request, self.template_name, {"item": item, "group": item.group})

    def post(self, request, item_id):
        """Handle Get Quote from item detail (no quiz data)."""
        item = get_object_or_404(
            Item.objects.prefetch_related("images", "features", "specs", "documents", "group"),
            pk=item_id, is_active=True
        )
        form = ParticipantForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, {"item": item, "group": item.group, "contact_form": form})

        # Build a minimal HTML note for ERP: just the interested item
        interested_rows = (
            f"<tr><td>Interested Product</td><td>{escape(item.name)}</td></tr>"
        )

        html_table = (
            "<table border='1' style='border-collapse:collapse;'>"
            "<tr><th>Requirement</th><th>Details</th></tr>"
            f"{interested_rows}"
            "</table>"
        )

        cd = form.cleaned_data  # name, email, phone, designation, company:contentReference[oaicite:1]{index=1}

        # Optional second note with person details (like your quiz flow)
        designation_note = (
            f"Name: {escape(cd.get('name',''))}<br>"
            f"Designation: {escape(cd.get('designation') or '-') if cd.get('designation') else '-'}<br>"
            f"Company: {escape(cd.get('company') or '-') if cd.get('company') else '-'}<br>"
            f"Phone: {escape(cd.get('phone') or '-') if cd.get('phone') else '-'}"
        )

        # Post to ERP (same pattern you already use in quiz contact step):contentReference[oaicite:2]{index=2}
        try:
            erp = ERPSettings.objects.first()
            if erp and erp.is_enabled:
                url = erp.base_url.rstrip("/") + f"/api/resource/{erp.lead_doctype}"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"token {erp.api_key}:{erp.api_secret}",
                }
                payload = {
                    "doctype": erp.lead_doctype,
                    "naming_series": erp.naming_series,
                    "deal_pipeline": erp.deal_pipeline,
                    "source": erp.source,
                    "status": erp.status,
                    "email_id": cd.get("email"),
                    "company_name": cd.get("company") or "",
                    "phone": cd.get("phone") or "",
                    "lead_name": cd.get("name") or "",
                    "notes": [
                        {"doctype": erp.lead_note_doctype, "note": html_table},
                        {"doctype": erp.lead_note_doctype, "note": designation_note},
                    ],
                }
                resp = requests.post(url, headers=headers, json=payload, allow_redirects=False, timeout=15)
                if 200 <= resp.status_code < 300:
                    messages.success(request, "Thanks! Your request has been sent.")
                else:
                    messages.warning(request, f"Saved locally, but ERP push failed ({resp.status_code}).")
            else:
                messages.success(request, "Thanks! Your request has been noted.")
        except Exception as e:
            messages.warning(request, f"Saved locally, but ERP push failed: {e}")

        # Re-render with success banner; form clears
        return render(request, self.template_name, {"item": item, "group": item.group})



class ContactView(View):
    template_name = "contactus/form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ContactForm()})

    def post(self, request):
        form = ContactForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, {"form": form})

        cd = form.cleaned_data
        msg = ContactMessage.objects.create(
            name=cd["name"],
            email=cd["email"],
            phone=cd.get("phone", ""),
            subject=cd.get("subject", ""),
            message=cd["message"],
        )

        # --- Optional: push into ERP as a Lead/Note (same pattern as Careers/Quiz) ---
        # --- Push Contact Us into ERP: Visitors Information (not Lead) ---
        # --- Push Contact Us into ERP: Visitor Information ---
        try:
            erp = ERPSettings.objects.first()
            if erp and erp.is_enabled:
                # Use the Visitor Information doctype
                visitor_doctype = "Visitor Information"

                # Safer URL: encode the doctype (space) to %20
                from urllib.parse import quote
                endpoint = f"/api/resource/{quote(visitor_doctype, safe='')}"
                url = erp.base_url.rstrip("/") + endpoint

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"token {erp.api_key}:{erp.api_secret}",
                }

                # Django form gives you the core fields (existing ContactForm)
                cd = form.cleaned_data

                # Extra fields come directly from POST (your HTML adds these inputs)
                naming_series = (request.POST.get("naming_series") or "").strip()
                source = (request.POST.get("source") or "").strip()
                status = (request.POST.get("status") or "").strip()
                state = (request.POST.get("state") or "").strip()
                contact_person = (request.POST.get("contact_person") or "").strip()
                contact_number = (request.POST.get("contact_number") or cd.get("phone", "")).strip()

                # Use your requested title format: "<name> | Territory : <state>"
                new_customer_name = f"{cd['name']} | Territory : {state}" if state else cd["name"]

                # prefer explicit `remark` if present, otherwise fall back to the message from the Django form
                remark = (request.POST.get("remark") or cd["message"]).strip()

                form_data = {
                    "naming_series": naming_series,  # ".FY.EXPO.####" (from hidden input)
                    "source": source,  # "Export Lead Generation" (from hidden input)
                    "status": status,  # "Open" (from hidden input)
                    "new_customer_name": new_customer_name,  # "<name> | Territory : <state>"
                    "state": state,
                    "contact_person": contact_person,  # company name
                    "contact_email_id": cd["email"],
                    "contact_number": contact_number,
                    "remark": remark,
                }

                resp = requests.post(url, headers=headers, json=form_data, timeout=15)

                # Optional: log for debugging during setup
                try:
                    print("ERP Visitors POST:", resp.status_code, resp.text[:400])
                except Exception:
                    pass

                if 200 <= resp.status_code < 300:
                    messages.success(request, "Thanks! We’ve received your message.")
                else:
                    messages.warning(request, f"Saved locally, but ERP push failed ({resp.status_code}).")
            else:
                messages.success(request, "Thanks! We’ve received your message.")
        except Exception as e:
            messages.warning(request, f"Saved locally, but ERP push failed: {e}")
        # --- /ERP push ---

        return redirect("configurator:contact_thanks")


def contact_thanks(request):
    return render(request, "contactus/thanks.html")




class CareerListView(View):
    def get(self, request):
        search_query = (request.GET.get("search", "") or "").strip().lower()
        qualification_filter = (request.GET.get("qualification", "") or "").strip()
        location_filter = (request.GET.get("location", "") or "").strip()

        try:
            jobs = fetch_job_list()
        except RuntimeError as e:
            messages.error(request, str(e))
            jobs = []

        qualification_options = sorted({j.get("designation", "") for j in jobs if j.get("designation")})
        location_options = sorted({j.get("territory", "") for j in jobs if j.get("territory")})

        filtered = []
        for job in jobs:
            nm = (job.get("name") or "").lower()
            ds = (job.get("designation") or "").lower()
            if search_query and (search_query not in nm and search_query not in ds):
                continue
            if qualification_filter and job.get("designation", "") != qualification_filter:
                continue
            if location_filter and job.get("territory", "") != location_filter:
                continue
            filtered.append(job)

        return render(
            request,
            "careers/job_list.html",
            {
                "jobs": filtered,
                "qualification_options": qualification_options,
                "locations": location_options,
                "search": search_query,
                "qualification": qualification_filter,
                "location": location_filter,
            },
        )

class CareerDetailView(View):
    def get(self, request, job_id: str):
        job = fetch_job_details(job_id)
        if not job:
            return render(request, "careers/not_found.html", status=404)
        return render(request, "careers/job_details.html", {"job": job})

class CareerApplyView(View):
    def get(self, request):
        initial = {
            "job_title": request.GET.get("job_title", ""),
            "designation": request.GET.get("designation", ""),
        }
        form = JobApplicationForm(initial=initial)
        return render(request, "careers/apply.html", {"form": form})

    def post(self, request):
        form = JobApplicationForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(request, "careers/apply.html", {"form": form})

        cd = form.cleaned_data
        filename = None
        if cd.get("resume_attachment"):
            safe_email = keep_at_secure_filename(cd.get("email_id"))
            new_name = safe_email + ".pdf"
            subdir = "resumes"
            storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, subdir))
            os.makedirs(storage.location, exist_ok=True)
            filename = storage.save(new_name, cd["resume_attachment"])

        payload = {
            "applicant_name": cd.get("applicant_name"),
            "job_title": cd.get("job_title"),
            "email_id": cd.get("email_id"),
            "designation": cd.get("designation"),
            "phone_number": cd.get("phone_number"),
            "country": cd.get("country"),
            "source": cd.get("source"),
            "cover_letter": cd.get("cover_letter"),
            "lower_range": cd.get("lower_range"),
            "upper_range": cd.get("upper_range"),
            "resume_attachment": os.path.basename(filename) if filename else "",
            # If you expose media URLs publicly, you can send an absolute resume link instead:
            # "resume_link": request.build_absolute_uri(storage.url(filename)) if filename else cd.get("resume_link"),
            "resume_link": cd.get("resume_link"),
        }

        try:
            resp = submit_applicant(payload)
            if 200 <= resp.status_code < 300:
                messages.success(request, "Form submitted successfully!")
                return redirect(reverse("configurator:career_apply"))
            messages.error(request, f"Error: {resp.status_code} — {resp.text[:500]}")
        except RuntimeError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error occurred: {e}")

        return render(request, "careers/apply.html", {"form": form})

class CareerTermsView(View):
    def get(self, request):
        return render(request, "careers/tnc.html")



def product_menu_api(request):
    groups = (
        ProductGroup.objects.filter(is_active=True)
        .order_by("name")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=Item.objects.filter(is_active=True)
                .only("id", "name")
                .order_by("name"),
                to_attr="menu_items",
            )
        )
    )
    data = []
    for g in groups:
        items = [{"name": it.name} for it in getattr(g, "menu_items", [])]
        if items:
            data.append({"name": g.name, "slug": g.slug, "items": items})
    return JsonResponse({"groups": data})


class PageView(View):
    def get(self, request, slug=None):
        if not slug:
            page = Page.objects.filter(is_active=True, is_home=True).first()
            if not page:
                return redirect("configurator:group_list")
        else:
            page = get_object_or_404(Page, slug=slug, is_active=True)

        if page.external_url:
            return redirect(page.external_url)

        return render(request, "configurator/detail.html", {"page": page})


def _score_items_from_session(session: QuizSession) -> Tuple[
    Dict[int, float], Dict[int, Item], Optional[Item], List[Tuple[Item, float]], List[Item]
]:
    """
    Recompute scores from persisted answers.
    Returns: (scores, items_by_id, recommended_item, breakdown, top_items)
    """
    answers_qs = session.answers.select_related("choice__question").prefetch_related(
        Prefetch("choice__impacts", queryset=ChoiceImpact.objects.select_related("item"))
    )

    scores: Dict[int, float] = defaultdict(float)

    for ans in answers_qs:
        q = ans.choice.question
        if hasattr(q, "affects_score") and not q.affects_score:
            continue
        for impact in ans.choice.impacts.all():
            item = impact.item
            if item.is_active and item.group_id == session.group_id:
                scores[item.id] += impact.score

    items_by_id: Dict[int, Item] = {}
    if scores:
        items = Item.objects.filter(id__in=scores.keys(), group=session.group, is_active=True)
        items_by_id = {it.id: it for it in items}

    recommended_item: Optional[Item] = None
    breakdown: List[Tuple[Item, float]] = []
    top_items: List[Item] = []

    if scores and items_by_id:
        breakdown = [(items_by_id[iid], sc) for iid, sc in scores.items()]
        breakdown.sort(key=lambda t: (-t[1], t[0].name))

        max_score = breakdown[0][1]
        top_items = [it for it, sc in breakdown if sc == max_score]
        recommended_item = sorted(top_items, key=lambda it: it.name)[0] if top_items else None

    return scores, items_by_id, recommended_item, breakdown, top_items


def _flatten_selected_choices(cleaned_data):
    """Return a list of selected Choice instances from cleaned_data (single + multi)."""
    selected = []
    for _, value in cleaned_data.items():
        if value is None:
            continue
        if hasattr(value, "__iter__") and not getattr(value, "_meta", None):
            selected.extend(list(value))
        else:
            selected.append(value)
    return selected


class GroupListView(View):
    def get(self, request):
        groups = (
            ProductGroup.objects.filter(is_active=True)
            .prefetch_related(
                Prefetch("items", queryset=Item.objects.filter(is_active=True).prefetch_related("images"))
            )
            .order_by("name")
        )

        groups_ctx = []
        for g in groups:
            hero_url = None
            if getattr(g, "hero_image", None) and g.hero_image:
                hero_url = g.hero_image.url
            else:
                for it in g.items.all():
                    img = next(iter(it.images.all()), None)
                    if img:
                        hero_url = img.image.url
                        break

            groups_ctx.append({
                "obj": g,
                "hero_url": hero_url,
                "items_count": g.items.count(),
            })

        return render(request, "configurator/group_list.html", {"groups_ctx": groups_ctx})


class QuizView(View):
    """
    Flow:
      - POST step='answers': save answers, compute result, render result page.
      - POST step='contact': save participant info, push Lead to ERP, re-render result.
    """

    def get(self, request, slug):
        group = get_object_or_404(ProductGroup, slug=slug, is_active=True)
        form = QuizForm(group=group)
        questions = group.questions.order_by("order")
        question_tags = questions.values_list("question_tag", flat=True)

        return render(request, "configurator/quiz.html", {
            "group": group,
            "form": form,
            "question_tags": question_tags,
        })

    def post(self, request, slug):
        group = get_object_or_404(ProductGroup, slug=slug, is_active=True)
        step = request.POST.get("step", "answers")

        # ------------------------------
        # Contact step: persist user info + ERP lead
        # ------------------------------
        if step == "contact":
            session_id = request.POST.get("session_id")
            session = get_object_or_404(QuizSession, id=session_id, group=group)

            form = ParticipantForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                session.name = data.get("name", "")
                session.email = data.get("email", "")
                session.phone = data.get("phone", "")
                session.designation = data.get("designation", "")
                session.company = data.get("company", "")
                interested_ids = request.POST.getlist("interested_items")
                setattr(session, "notes", f"Interested in item IDs: {', '.join(interested_ids)}")
                try:
                    session.save(update_fields=["name", "email", "phone", "designation", "company"])
                except Exception:
                    session.save()

                # --- ERP INTEGRATION ---
                try:
                    erp = ERPSettings.objects.first()
                    if erp and erp.is_enabled:
                        # 1) Resolve interested items (as you already did)
                        interested_items = list(
                            Item.objects.filter(id__in=interested_ids).values_list("name", flat=True)
                        )

                        # 2) Build "Interested Products" rows
                        interested_rows = "".join(
                            f"<tr><td>Interested Product</td><td>{escape(name)}</td></tr>"
                            for name in interested_items
                        ) or "<tr><td>Interested Product</td><td>(not specified)</td></tr>"

                        # 3) Gather selected choices grouped by question
                        #    (One Answer per selected choice; group them by the question)
                        answers = (
                            session.answers
                            .select_related("question", "choice")
                            .order_by("question__order", "choice__order", "id")
                        )

                        from collections import defaultdict
                        by_question = defaultdict(list)
                        for ans in answers:
                            q_label = (ans.question.question_tag or ans.question.text or "").strip()
                            c_label = (ans.choice.text or "").strip()
                            if q_label and c_label:
                                by_question[q_label].append(c_label)

                        # 4) Build "Your selections" rows (Question → comma-joined choices)
                        selection_rows = "".join(
                            f"<tr><td>{escape(q)}</td><td>{escape(', '.join(choices))}</td></tr>"
                            for q, choices in by_question.items()
                        ) or "<tr><td>User selections</td><td>(none)</td></tr>"

                        # 5) Final HTML table with two sections
                        html_table = (
                            "<table border='1' style='border-collapse:collapse;'>"
                            "<tr><th>Requirement</th><th>Details</th></tr>"
                            f"{interested_rows}"
                            "<tr><th colspan='2' style='text-align:left;background:#f6f6f6;'>Your selections</th></tr>"
                            f"{selection_rows}"
                            "</table>"
                        )

                        # 6) Keep your existing designation note
                        designation_note = (
                            f"Name: {escape(session.name)}<br>"
                            f"Designation: {escape(session.designation or '-')}<br>"
                            f"Company: {escape(session.company or '-')}<br>"
                            f"Phone: {escape(session.phone or '-')}"
                        )

                        url = erp.base_url.rstrip("/") + f"/api/resource/{erp.lead_doctype}"
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"token {erp.api_key}:{erp.api_secret}",
                        }
                        payload = {
                            "doctype": erp.lead_doctype,
                            "naming_series": erp.naming_series,
                            "deal_pipeline": erp.deal_pipeline,
                            "source": erp.source,
                            "status": erp.status,
                            "email_id": session.email,
                            "company_name": session.company or "",
                            "phone": session.phone or "",
                            "lead_name": session.name or "",
                            "notes": [
                                {"doctype": erp.lead_note_doctype, "note": html_table},
                                {"doctype": erp.lead_note_doctype, "note": designation_note},
                            ],
                        }

                        resp = requests.post(
                            url, headers=headers, json=payload, allow_redirects=False, timeout=15
                        )
                        request.erp_push_ok = (200 <= resp.status_code < 300)
                        request.erp_push_status = resp.status_code
                    else:
                        request.erp_push_ok = False
                        request.erp_push_status = "ERP disabled or not configured"
                except Exception as e:
                    request.erp_push_ok = False
                    request.erp_push_status = f"ERP error: {e}"
                # --- /ERP INTEGRATION ---

                # Recompute recommendation so result page stays consistent
                _, _, recommended_item, breakdown, top_items = _score_items_from_session(session)
                family = Item.objects.filter(group=group, is_active=True).exclude(
                    id__in=[it.id for it in top_items]
                )[:8]

                return render(
                    request,
                    "configurator/result.html",
                    {
                        "group": group,
                        "recommended_items": top_items,
                        "recommended_item": recommended_item,
                        "breakdown": breakdown,
                        "family_items": family,
                        "session": session,
                        "quote_submitted": True,  # flag for UI
                        "erp_push_ok": getattr(request, "erp_push_ok", None),
                        "erp_push_status": getattr(request, "erp_push_status", None),
                    },
                )

            # Invalid contact form → re-render result with errors but keep prior recs
            _, _, recommended_item, breakdown, top_items = _score_items_from_session(session)
            family = Item.objects.filter(group=group, is_active=True).exclude(
                id__in=[it.id for it in top_items]
            )[:8]
            return render(
                request,
                "configurator/result.html",
                {
                    "group": group,
                    "recommended_items": top_items,
                    "recommended_item": recommended_item,
                    "breakdown": breakdown,
                    "family_items": family,
                    "session": session,
                    "quote_submitted": False,
                    "contact_form": form,
                },
            )

        # ------------------------------
        # Answers step: grade quiz and render result
        # ------------------------------
        quiz_form = QuizForm(group=group, data=request.POST)
        if not quiz_form.is_valid():
            return render(request, "configurator/quiz.html", {"group": group, "form": quiz_form})

        choices = _flatten_selected_choices(quiz_form.cleaned_data)
        session = QuizSession.objects.create(group=group, recommended_item=None)
        for ch in choices:
            Answer.objects.create(session=session, question=ch.question, choice=ch)

        _, _, recommended_item, breakdown, top_items = _score_items_from_session(session)

        if recommended_item and session.recommended_item_id != recommended_item.id:
            session.recommended_item = recommended_item
            session.save(update_fields=["recommended_item"])

        family = Item.objects.filter(group=group, is_active=True).exclude(
            id__in=[it.id for it in top_items]
        )[:8]

        return render(
            request,
            "configurator/result.html",
            {
                "group": group,
                "recommended_items": top_items,
                "recommended_item": recommended_item,
                "breakdown": breakdown,
                "family_items": family,
                "session": session,
                "quote_submitted": False,
            },
        )
