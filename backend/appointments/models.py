from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from institutions.models import Institution


class AppointmentType(models.TextChoices):
    COURT_HEARING = "COURT_HEARING", "Court hearing"
    MEDICAL = "MEDICAL", "Medical appointment"
    COUNSELLING = "COUNSELLING", "Counselling session"
    LEGAL_AID = "LEGAL_AID", "Legal aid meeting"
    FOLLOW_UP = "FOLLOW_UP", "Follow-up visit"
    OTHER = "OTHER", "Other"


class Attendees(models.TextChoices):
    CHILD_AND_CAREGIVER = "CHILD_AND_CAREGIVER", "The child and the complainant / caregiver"
    CHILD = "CHILD", "The child"
    CAREGIVER = "CAREGIVER", "The complainant / caregiver"
    NOT_REQUIRED = "NOT_REQUIRED", "Family attendance not required"


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    RESCHEDULED = "RESCHEDULED", "Rescheduled"
    COMPLETED = "COMPLETED", "Attended / completed"
    MISSED = "MISSED", "Missed — needs follow-up"
    CANCELLED = "CANCELLED", "Cancelled"


class Appointment(TimeStampedModel):
    case = models.ForeignKey("cases.ChildCase", on_delete=models.CASCADE, related_name="appointments")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="appointments")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    type = models.CharField(max_length=20, choices=AppointmentType.choices)
    scheduled_for = models.DateTimeField(db_index=True)
    previous_scheduled_for = models.DateTimeField(null=True, blank=True)
    public_location = models.CharField(max_length=200, help_text="Safe to show to the beneficiary.")
    internal_note = models.CharField(max_length=500, blank=True)
    beneficiary_note = models.CharField(max_length=300, blank=True, help_text="Plain-language note for the family.")
    visible_to_beneficiary = models.BooleanField(default=True)
    attendees = models.CharField(max_length=20, choices=Attendees.choices, default=Attendees.CHILD_AND_CAREGIVER)
    status = models.CharField(max_length=12, choices=AppointmentStatus.choices, default=AppointmentStatus.SCHEDULED, db_index=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["scheduled_for"]
