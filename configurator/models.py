# configurator/models.py
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify
from PIL import Image
from ckeditor_uploader.fields import RichTextUploadingField


class ContactMessage(models.Model):
    name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # status/processing flags (optional)
    handled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} — {self.subject or 'No subject'}"




# === Mini CMS Pages ===
class Page(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, help_text="URL path, e.g. 'about', 'home'")
    is_active = models.BooleanField(default=True)
    menu_order = models.PositiveIntegerField(default=0, help_text="Sort order for nav")

    # Content
    body = models.TextField(blank=True, help_text="Main HTML/Markdown (rendered safely in template)")
    # Per-page footer (falls back to global site footer if left blank)
    footer_html = models.TextField(blank=True)

    # Hero
    show_hero = models.BooleanField(default=True, help_text="Show hero section on this page")
    hero_image = models.ImageField(upload_to="page_heroes/", blank=True, null=True)
    hero_alt = models.CharField(max_length=200, blank=True)
    hero_caption = models.CharField(max_length=200, blank=True)

    # External redirect (e.g., WordPress)
    external_url = models.URLField(blank=True, help_text="If set, this page redirects to this URL")

    # Optional: mark as homepage (only one should be True)
    is_home = models.BooleanField(default=False, help_text="Make this the site homepage")

    #  switched to rich text with uploads
    body = RichTextUploadingField(blank=True)
    footer_html = RichTextUploadingField(blank=True)

    #  NEW: page-specific CSS editable from admin
    custom_css = models.TextField(blank=True, help_text="Optional CSS for this page only.")

    class Meta:
        ordering = ["menu_order", "title"]

    def __str__(self):
        return self.title





class ItemFeature(models.Model):
    item = models.ForeignKey("Item", on_delete=models.CASCADE, related_name="features")
    text = models.CharField(max_length=300)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item.name} — {self.text}"


# =========================
# Image constraints (tweak)
# =========================
# Max bounding boxes (pixels). Images larger than these will be downscaled on save().
QUESTION_MAX_W, QUESTION_MAX_H = 1200, 800     # question figure/hero
CHOICE_MAX_W,   CHOICE_MAX_H   = 500,  500     # compact choice image
# Optional: max file size in bytes (None to disable)
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def _validate_file_size(field_file, label: str):
    """Raise ValidationError if file too big (if MAX_FILE_SIZE_BYTES is set)."""
    if MAX_FILE_SIZE_BYTES is None:
        return
    if field_file and hasattr(field_file, "size") and field_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"{label} image too large: {field_file.size/1024:.0f}KB. "
            f"Max allowed is {MAX_FILE_SIZE_BYTES/1024:.0f}KB."
        )


def _validate_img_dimensions(img: Image.Image, max_w: int, max_h: int, label: str):
    """Raise ValidationError if image exceeds bounding box."""
    w, h = img.size
    if w > max_w or h > max_h:
        raise ValidationError(
            f"{label} image dimensions {w}×{h}px exceed {max_w}×{max_h}px."
        )


def _downscale_to_box(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Return copy downscaled to fit in (max_w, max_h) preserving aspect ratio."""
    w, h = img.size
    if w <= max_w and h <= max_h:
        return img
    img = img.copy()
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def _save_resized_to_field(img: Image.Image, field: models.ImageField, fmt_hint: str = "JPEG", quality: int = 88):
    """
    Encode Image into field (in-place, without calling model.save()).
    Default to JPEG with quality, keep PNG if the original name ends with .png.
    """
    buf = BytesIO()
    fmt = "PNG" if str(fmt_hint).lower().endswith(".png") else "JPEG"
    save_params = {"format": fmt}
    if fmt == "JPEG":
        save_params.update({"optimize": True, "quality": quality})
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    img.save(buf, **save_params)

    content = ContentFile(buf.getvalue())
    original_name = Path(field.name or "upload").name
    stem = Path(original_name).stem or "image"
    ext = ".png" if fmt == "PNG" else ".jpg"
    new_name = f"{stem}_resized{ext}"
    field.save(new_name, content, save=False)


# =========================
# Core domain models
# =========================

class ProductGroup(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    hero_image = models.ImageField(upload_to="group_heroes/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name



class Item(models.Model):
    group = models.ForeignKey(ProductGroup, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=140)
    description = RichTextUploadingField(blank=True)
    is_active = models.BooleanField(default=True)

    # NEW
    item_code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    class Meta:
        unique_together = ("group", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.group.name})"


class ItemFeature(models.Model):
    item = models.ForeignKey("Item", on_delete=models.CASCADE, related_name="features")
    text = models.CharField(max_length=300)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item.name} — {self.text}"



class Question(models.Model):
    INPUT_SINGLE = "single"
    INPUT_MULTI  = "multi"
    INPUT_TYPES = [
        (INPUT_SINGLE, "Single choice (radio)"),
        (INPUT_MULTI,  "Multiple choice (checkboxes)"),
    ]

    group = models.ForeignKey(ProductGroup, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=300)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    # Input behavior
    input_type = models.CharField(max_length=10, choices=INPUT_TYPES, default=INPUT_SINGLE)
    affects_score = models.BooleanField(
        default=True,
        help_text="If off, selections from this question will NOT change scores (informational only)."
    )
    question_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Short title or tag for this question (under 10 words)."
    )
    # NEW: optional image with enforced dimensions
    image = models.ImageField(upload_to="question_images/", blank=True, null=True)
    image_width = models.PositiveIntegerField(default=0, editable=False)
    image_height = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["group", "order", "id"]

    def __str__(self) -> str:
        return f"[{self.group.name}] {self.text}"

    # Validation and autoscale
    def clean(self):
        super().clean()
        if self.image and hasattr(self.image, "file"):
            _validate_file_size(self.image.file, "Question")
            try:
                img = Image.open(self.image)
                img.verify()  # basic integrity check
            except Exception:
                raise ValidationError("Question image is not a valid image file.")
            # re-open after verify for size
            img = Image.open(self.image)
            _validate_img_dimensions(img, QUESTION_MAX_W, QUESTION_MAX_H, "Question")

    def save(self, *args, **kwargs):
        # Auto-downscale to limits to avoid heavy images in the quiz
        if self.image and hasattr(self.image, "file"):
            try:
                img = Image.open(self.image)
                img.load()
                img = _downscale_to_box(img, QUESTION_MAX_W, QUESTION_MAX_H)
                _save_resized_to_field(img, self.image, fmt_hint=self.image.name)
                self.image_width, self.image_height = img.size
            except Exception:
                # If anything fails during processing, proceed with original file
                pass
        super().save(*args, **kwargs)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=240)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # NEW: optional image with enforced dimensions
    image = models.ImageField(upload_to="choice_images/", blank=True, null=True)
    image_width = models.PositiveIntegerField(default=0, editable=False)
    image_height = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["question", "order", "id"]

    def __str__(self) -> str:
        return self.text

    def clean(self):
        super().clean()
        if self.image and hasattr(self.image, "file"):
            _validate_file_size(self.image.file, "Choice")
            try:
                img = Image.open(self.image)
                img.verify()
            except Exception:
                raise ValidationError("Choice image is not a valid image file.")
            img = Image.open(self.image)
            _validate_img_dimensions(img, CHOICE_MAX_W, CHOICE_MAX_H, "Choice")

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, "file"):
            try:
                img = Image.open(self.image)
                img.load()
                img = _downscale_to_box(img, CHOICE_MAX_W, CHOICE_MAX_H)
                _save_resized_to_field(img, self.image, fmt_hint=self.image.name)
                self.image_width, self.image_height = img.size
            except Exception:
                pass
        super().save(*args, **kwargs)


class ChoiceImpact(models.Model):
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name="impacts")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="impacted_by")
    score = models.FloatField(default=1.0)

    class Meta:
        unique_together = ("choice", "item")

    def __str__(self) -> str:
        return f"{self.choice} -> {self.item} (+{self.score})"


class QuizSession(models.Model):
    group = models.ForeignKey(ProductGroup, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    recommended_item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)

    # Participant info
    name = models.CharField(max_length=140, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    designation = models.CharField(max_length=140, blank=True)
    company = models.CharField(max_length=180, blank=True)

    interested_items = models.ManyToManyField('Item', blank=True, related_name='interested_sessions')

    def __str__(self) -> str:
        return f"Session #{self.pk} — {self.group.name}"


class Answer(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.ForeignKey(Choice, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.session_id}: {self.question_id} -> {self.choice_id}"


class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="item_images/")  # requires Pillow
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Image for {self.item.name}"





class ItemSpec(models.Model):
    item = models.ForeignKey("Item", on_delete=models.CASCADE, related_name="specs")
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=400, blank=True)
    unit  = models.CharField(max_length=40, blank=True)
    order = models.PositiveIntegerField(default=0)
    highlight = models.BooleanField(default=False, help_text="Emphasize this spec in UI")

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("item", "label")]

    def __str__(self):
        v = f"{self.value}{(' ' + self.unit) if self.unit else ''}"
        return f"{self.label}: {v}" if v else self.label


class ItemDocument(models.Model):
    item = models.ForeignKey("Item", on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="item_docs/")   # Supports PDF, DOC, etc.
    title = models.CharField(max_length=200, blank=True)  # Optional display title
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title or f"Document for {self.item.name}"


# --- ERP integration settings (singleton-ish) ---
class ERPSettings(models.Model):

    is_enabled = models.BooleanField(default=False)
    base_url = models.URLField(help_text="Base API URL, e.g. https://erp.example.com")
    api_key = models.CharField(max_length=200)
    api_secret = models.CharField(max_length=200)
    lead_doctype = models.CharField(max_length=60, default="Lead")
    lead_note_doctype = models.CharField(max_length=60, default="Lead Note")
    naming_series = models.CharField(max_length=120, blank=True, default=".FY.LEADM.####")
    deal_pipeline = models.CharField(max_length=120, blank=True, default="Machine")
    source = models.CharField(max_length=120, blank=True, default="Configurator")
    status = models.CharField(max_length=120, blank=True, default="Lead")

    class Meta:
        verbose_name = "ERP Settings"
        verbose_name_plural = "ERP Settings"

    def __str__(self):
        return f"ERP Settings ({'enabled' if self.is_enabled else 'disabled'})"
