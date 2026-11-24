from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from institutions.models import Institution


class ServiceCategory(models.TextChoices):
    MEDICAL = "MEDICAL", "Medical care"
    PSYCHOSOCIAL = "PSYCHOSOCIAL", "Counselling & psychosocial support"
    LEGAL_AID = "LEGAL_AID", "Legal aid"
    SHELTER = "SHELTER", "Safe shelter"
    PROBATION = "PROBATION", "Probation & social welfare"
    HELPLINE = "HELPLINE", "Helpline"


class SupportService(TimeStampedModel):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="services")
    category = models.CharField(max_length=20, choices=ServiceCategory.choices, db_index=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=500)
    public_contact = models.CharField(max_length=120, blank=True)
    hours = models.CharField(max_length=120, blank=True)
    districts = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    is_free = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class AssistanceType(models.TextChoices):
    CALL_BACK = "CALL_BACK", "Please call me back"
    QUESTION = "QUESTION", "I have a question about my case"
    APPOINTMENT_HELP = "APPOINTMENT_HELP", "Help to attend an appointment"
    SAFETY_CONCERN = "SAFETY_CONCERN", "I do not feel safe"
    SUPPORT_SERVICE = "SUPPORT_SERVICE", "I need a support service"
    OTHER = "OTHER", "Something else"


class AssistanceStatus(models.TextChoices):
    OPEN = "OPEN", "Received"
    IN_PROGRESS = "IN_PROGRESS", "Being handled"
    RESOLVED = "RESOLVED", "Responded"
    CLOSED = "CLOSED", "Closed"


class AssistanceRequest(TimeStampedModel):
    case = models.ForeignKey("cases.ChildCase", on_delete=models.CASCADE, related_name="assistance_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assistance_requests")
    request_type = models.CharField(max_length=20, choices=AssistanceType.choices)
    message = models.CharField(max_length=500, blank=True)
    preferred_contact_time = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=AssistanceStatus.choices, default=AssistanceStatus.OPEN, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_assistance")
    response_message = models.CharField(max_length=500, blank=True, help_text="Shown to the requester.")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
