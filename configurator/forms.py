
# configurator/forms.py
from django import forms
from django.core.exceptions import ValidationError
import re
from .models import ProductGroup, Question

class ContactForm(forms.Form):
    name = forms.CharField(max_length=140)
    email = forms.EmailField()
    phone = forms.CharField(max_length=40, required=False)
    subject = forms.CharField(max_length=180, required=False)
    message = forms.CharField(widget=forms.Textarea)

EMAIL_SAFE = re.compile(r'(?u)[^-\w.@]')

def keep_at_secure_filename(s: str) -> str:
    s = (s or "").strip().replace(" ", "_")
    return EMAIL_SAFE.sub("", s)

class JobApplicationForm(forms.Form):
    applicant_name = forms.CharField(max_length=200)
    job_title = forms.CharField(max_length=200, required=False)
    designation = forms.CharField(max_length=200, required=False)
    email_id = forms.EmailField()
    phone_number = forms.CharField(max_length=50, required=False)
    country = forms.CharField(max_length=120, required=False)
    cover_letter = forms.CharField(widget=forms.Textarea, required=False)
    lower_range = forms.CharField(required=False)
    upper_range = forms.CharField(required=False)
    resume_link = forms.URLField(required=False)
    source = forms.CharField(max_length=120, required=False)
    resume_attachment = forms.FileField(required=False)

    def clean_resume_attachment(self):
        f = self.cleaned_data.get("resume_attachment")
        if not f:
            return f
        name = (f.name or "")
        if "." not in name:
            raise ValidationError("Invalid file name.")
        ext = name.rsplit(".", 1)[1].lower()
        if ext != "pdf":
            raise ValidationError("Invalid file format! Please upload a PDF.")
        if f.size > 8 * 1024 * 1024:
            raise ValidationError("File too large (max 8MB).")
        return f


class QuizForm(forms.Form):
    def __init__(self, group: ProductGroup, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group
        qs = group.questions.filter(is_active=True).order_by("order", "id").prefetch_related("choices")
        for q in qs:
            choices_qs = q.choices.filter(is_active=True).order_by("order", "id")
            if getattr(Question, "INPUT_MULTI", None) and q.input_type == Question.INPUT_MULTI:
                field = forms.ModelMultipleChoiceField(
                    label=q.text,
                    queryset=choices_qs,
                    widget=forms.CheckboxSelectMultiple,
                    required=q.is_required,
                )
                field.widget.attrs["data_multi"] = "1"
            else:
                field = forms.ModelChoiceField(
                    label=q.text,
                    queryset=choices_qs,
                    widget=forms.RadioSelect,
                    required=q.is_required,
                    empty_label=None,
                )
                field.widget.attrs["data_multi"] = "0"
            self.fields[f"q_{q.id}"] = field

class ParticipantForm(forms.Form):
    name = forms.CharField(max_length=140, label="Full name")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=40, label="Phone number")
    designation = forms.CharField(max_length=140, label="Designation (optional)", required=False)
    company = forms.CharField(max_length=180, label="Company (optional)", required=False)
