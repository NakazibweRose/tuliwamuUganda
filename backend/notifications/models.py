from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField
from core.models import TimeStampedModel


class NotificationType(models.TextChoices):
    REFERRAL_RECEIVED = "REFERRAL_RECEIVED", "New referral received"
    REFERRAL_ACKNOWLEDGED = "REFERRAL_ACKNOWLEDGED", "Referral acknowledged"
    REFERRAL_UPDATED = "REFERRAL_UPDATED", "Referral updated"
    REFERRAL_FOLLOW_UP = "REFERRAL_FOLLOW_UP", "Referral requires follow-up"
    APPOINTMENT_SCHEDULED = "APPOINTMENT_SCHEDULED", "Appointment scheduled"
    APPOINTMENT_CHANGED = "APPOINTMENT_CHANGED", "Appointment changed"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", "Appointment approaching"
    APPOINTMENT_MISSED = "APPOINTMENT_MISSED", "Missed appointment"
    CASE_UPDATE = "CASE_UPDATE", "Important case update"
    UPDATE_NEEDS_REVIEW = "UPDATE_NEEDS_REVIEW", "Beneficiary update needs review"
    GRANT_NEEDS_APPROVAL = "GRANT_NEEDS_APPROVAL", "Access grant needs approval"
    ASSISTANCE_REQUEST = "ASSISTANCE_REQUEST", "Assistance requested"
    ASSISTANCE_RESPONSE = "ASSISTANCE_RESPONSE", "Response to your request"
    SUPPORT_COMPLETED = "SUPPORT_COMPLETED", "Support service completed"
    ANONYMOUS_REPORT = "ANONYMOUS_REPORT", "New anonymous report"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE", "Follow-up assigned"


class Notification(TimeStampedModel):
    """In-app notification. title/body are rendered from templates and never contain case details."""

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True, help_text="Frontend route; contains only opaque IDs.")
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dedup_key = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["recipient", "dedup_key"], condition=~models.Q(dedup_key=""), name="uniq_notification_dedup")
        ]


class Channel(models.TextChoices):
    IN_APP = "IN_APP", "In-app only"
    SMS = "SMS", "SMS + in-app"
    EMAIL = "EMAIL", "Email + in-app"


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference")
    preferred_channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    preferred_language = models.CharField(max_length=5, default="en")
    sms_consent = models.BooleanField(default=False)
    safe_phone = EncryptedTextField(blank=True, help_text="A number confirmed safe to receive discreet messages.")
    quiet_hours_start = models.PositiveSmallIntegerField(default=20, help_text="Hour (0–23) after which no SMS is sent.")
    quiet_hours_end = models.PositiveSmallIntegerField(default=7, help_text="Hour (0–23) before which no SMS is sent.")
    consent_reference = models.CharField(
        max_length=200, blank=True, help_text="Reference to the recorded consent or lawful authorisation."
    )
    consent_recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    consent_recorded_at = models.DateTimeField(null=True, blank=True)
