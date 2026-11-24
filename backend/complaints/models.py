"""Complainant reports (written and/or voice) that police verify before an official case exists.

Data-protection notes:
* The statement, transcript, translation and AI summary are encrypted at rest (EncryptedTextField).
* Audio is stored Fernet-encrypted in the database (ComplaintAudio.data), never on disk, and is only
  streamed to police officers of the assigned station (each play is audited).
* The complainant can see the status of their report and messages from police — never the AI output,
  transcripts, police notes or case documents.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.fields import EncryptedTextField
from core.models import TimeStampedModel


class Concerning(models.TextChoices):
    SELF = "SELF", "Me (I am the child)"
    MY_CHILD = "MY_CHILD", "My child"
    CHILD_IN_CARE = "CHILD_IN_CARE", "A child in my care"
    OTHER_CHILD = "OTHER_CHILD", "Another child I know"


class ComplaintStatus(models.TextChoices):
    PROCESSING = "PROCESSING", "Being prepared"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION", "Waiting for police verification"
    NEEDS_INFO = "NEEDS_INFO", "Police need more information"
    REGISTERED = "REGISTERED", "Verified — case registered"
    NOT_REGISTERED = "NOT_REGISTERED", "Reviewed — not registered"


class AiStatus(models.TextChoices):
    PENDING = "PENDING", "Waiting"
    PROCESSING = "PROCESSING", "Running"
    DONE = "DONE", "Done"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Not used (no consent or AI not configured)"


class Urgency(models.TextChoices):
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"


# UI language codes → ISO 639-3 codes used by Sunbird AI.
SUNBIRD_LANG = {"en": "eng", "lg": "lug", "ach": "ach", "nyn": "nyn", "teo": "teo", "sw": "swa"}


def default_respond_by():
    return timezone.now() + timedelta(hours=settings.COMPLAINT_RESPONSE_HOURS)


class Complaint(TimeStampedModel):
    reference = models.CharField(max_length=12, unique=True)
    complainant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaints")
    concerning = models.CharField(max_length=16, choices=Concerning.choices)
    child_age_range = models.CharField(max_length=8, default="UNKNOWN")
    district = models.CharField(max_length=80)
    region = models.CharField(max_length=10, blank=True)
    immediate_danger = models.BooleanField(default=False)
    language = models.CharField(max_length=5, default="en", help_text="Language the complainant wrote or spoke in.")
    reply_language = models.CharField(max_length=5, default="en", help_text="Language for answers to the complainant.")
    written_statement = EncryptedTextField(blank=True)
    ai_consent = models.BooleanField(default=False)

    # AI pipeline output (police-only).
    ai_status = models.CharField(max_length=12, choices=AiStatus.choices, default=AiStatus.PENDING)
    ai_error = models.CharField(max_length=120, blank=True)
    ai_model = models.CharField(max_length=60, blank=True)
    ai_processed_at = models.DateTimeField(null=True, blank=True)
    transcript = EncryptedTextField(blank=True, help_text="Speech-to-text in the original language.")
    english_text = EncryptedTextField(blank=True, help_text="Statement + transcript translated to English.")
    ai_category = models.CharField(max_length=20, blank=True)
    ai_urgency = models.CharField(max_length=8, choices=Urgency.choices, blank=True)
    ai_summary = EncryptedTextField(blank=True)
    ai_key_facts = EncryptedTextField(blank=True, help_text="JSON list of short facts.")

    status = models.CharField(max_length=24, choices=ComplaintStatus.choices, default=ComplaintStatus.PROCESSING, db_index=True)
    respond_by = models.DateTimeField(default=default_respond_by)
    assigned_institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT, related_name="complaints")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    internal_note = EncryptedTextField(blank=True, help_text="Police-only verification note.")
    case = models.OneToOneField("cases.ChildCase", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_complaint")
    complainant_can_follow_case = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["assigned_institution", "status"])]

    @property
    def is_overdue(self):
        return self.status in {ComplaintStatus.PROCESSING, ComplaintStatus.AWAITING_VERIFICATION} and timezone.now() > self.respond_by

    def __str__(self):
        return self.reference


class ComplaintAudio(TimeStampedModel):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="audio")
    data = models.BinaryField(help_text="Fernet-encrypted audio bytes.")
    mime_type = models.CharField(max_length=60)
    size_bytes = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)


class ComplaintMessage(TimeStampedModel):
    """Two-way thread between the complainant and the police, auto-translated where possible."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    from_police = models.BooleanField()
    text = EncryptedTextField()
    text_language = models.CharField(max_length=5, default="en")
    translated_text = EncryptedTextField(blank=True)
    translated_language = models.CharField(max_length=5, blank=True)
    machine_translated = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class ComplaintEvent(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    action = models.CharField(max_length=40)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["created_at"]
