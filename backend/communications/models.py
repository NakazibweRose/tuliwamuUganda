from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField
from core.models import TimeStampedModel


class AnonymousCategory(models.TextChoices):
    SEXUAL_ABUSE = "SEXUAL_ABUSE", "Sexual abuse"
    PHYSICAL_VIOLENCE = "PHYSICAL_VIOLENCE", "Physical violence"
    NEGLECT = "NEGLECT", "Neglect"
    EXPLOITATION = "EXPLOITATION", "Exploitation / child labour"
    TRAFFICKING = "TRAFFICKING", "Trafficking"
    OTHER = "OTHER", "Other concern"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified — pending assessment"
    CREDIBLE = "CREDIBLE", "Assessed as needing action"
    NOT_SUBSTANTIATED = "NOT_SUBSTANTIATED", "Not substantiated"
    DUPLICATE = "DUPLICATE", "Duplicate"
    MALICIOUS = "MALICIOUS", "Malicious / spam"


class ReviewStatus(models.TextChoices):
    NEW = "NEW", "New"
    URGENT = "URGENT", "Flagged for urgent safeguarding assessment"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    REFERRED = "REFERRED", "Passed to a responsible service"
    CONVERTED = "CONVERTED", "Converted to an official case"
    CLOSED = "CLOSED", "Closed"


class Channel(models.TextChoices):
    USSD = "USSD", "USSD (Africa's Talking)"
    SIMULATOR = "SIMULATOR", "USSD web simulator (demo)"


class AnonymousReport(TimeStampedModel):
    """Unverified concern received anonymously. Kept apart from official cases until an officer reviews it."""

    reference_code = models.CharField(max_length=12, unique=True)
    pin_hash = models.CharField(max_length=128)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    category = models.CharField(max_length=20, choices=AnonymousCategory.choices)
    immediate_danger = models.CharField(max_length=8, choices=[("YES", "Yes"), ("NO", "No"), ("UNSURE", "Not sure")])
    general_location = models.CharField(max_length=60)
    description = EncryptedTextField()
    preferred_language = models.CharField(max_length=5, default="en")
    optional_safe_contact = EncryptedTextField(blank=True, help_text="Only if the reporter chose to give one.")
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED)
    review_status = models.CharField(max_length=15, choices=ReviewStatus.choices, default=ReviewStatus.NEW, db_index=True)
    assigned_institution = models.ForeignKey("institutions.Institution", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    converted_case = models.OneToOneField("cases.ChildCase", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_anonymous_report")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    failed_status_checks = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]


class AnonymousReportEvent(TimeStampedModel):
    report = models.ForeignKey(AnonymousReport, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=40)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["created_at"]


class UssdSession(models.Model):
    """Short-lived USSD state. The phone number is never stored here. Purged after expiry."""

    session_id = models.CharField(max_length=100, primary_key=True)
    selected_language = models.CharField(max_length=5, blank=True)
    current_menu = models.CharField(max_length=30)
    temporary_session_data = models.JSONField(default=dict)
    last_text = models.TextField(blank=True)
    last_response = models.TextField(blank=True)
    invalid_attempts = models.PositiveSmallIntegerField(default=0)
    report = models.ForeignKey(AnonymousReport, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)


class SmsStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    DEFERRED = "DEFERRED", "Deferred (quiet hours)"
    SIMULATED = "SIMULATED", "Simulated — not sent to any phone"
    SUBMITTED = "SUBMITTED", "Accepted by provider (not yet delivered)"
    DELIVERED = "DELIVERED", "Delivered (confirmed by provider)"
    FAILED = "FAILED", "Failed"
    BLOCKED = "BLOCKED", "Not sent — no consent or safe number"


class SmsMessage(TimeStampedModel):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sms_messages")
    phone_encrypted = EncryptedTextField(blank=True)
    phone_masked = models.CharField(max_length=20, blank=True)
    message_template = models.CharField(max_length=60)
    language = models.CharField(max_length=5)
    notification_type = models.CharField(max_length=30, db_index=True)
    body = models.CharField(max_length=320)
    provider = models.CharField(max_length=20)
    delivery_status = models.CharField(max_length=10, choices=SmsStatus.choices, default=SmsStatus.QUEUED, db_index=True)
    provider_message_id = models.CharField(max_length=100, blank=True, db_index=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    dedup_key = models.CharField(max_length=200, unique=True)
    send_after = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
