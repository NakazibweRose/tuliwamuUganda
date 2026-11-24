from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField
from core.models import TimeStampedModel
from institutions.models import Institution, InstitutionType


class ReferralCategory(models.TextChoices):
    MEDICAL = "MEDICAL", "Medical"
    FORENSIC = "FORENSIC", "Forensic"
    PROSECUTION = "PROSECUTION", "Prosecution review (ODPP)"
    COURT = "COURT", "Court procedural handoff"
    PROBATION = "PROBATION", "Probation & social welfare"
    LEGAL_AID = "LEGAL_AID", "Legal aid"
    PSYCHOSOCIAL = "PSYCHOSOCIAL", "Psychosocial support"
    SHELTER = "SHELTER", "Protection & shelter"


# Which institution types may receive which referral category.
CATEGORY_RECEIVER_TYPES = {
    ReferralCategory.MEDICAL: {InstitutionType.HEALTH},
    ReferralCategory.FORENSIC: {InstitutionType.FORENSIC},
    ReferralCategory.PROSECUTION: {InstitutionType.ODPP},
    ReferralCategory.COURT: {InstitutionType.COURT},
    ReferralCategory.PROBATION: {InstitutionType.PROBATION},
    ReferralCategory.LEGAL_AID: {InstitutionType.LEGAL_AID},
    ReferralCategory.PSYCHOSOCIAL: {InstitutionType.PSYCHOSOCIAL, InstitutionType.HEALTH, InstitutionType.PROBATION},
    ReferralCategory.SHELTER: {InstitutionType.SHELTER, InstitutionType.PROBATION},
}


class Priority(models.TextChoices):
    ROUTINE = "ROUTINE", "Routine"
    URGENT = "URGENT", "Urgent"
    EMERGENCY = "EMERGENCY", "Emergency"


class ReferralStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    RETURNED = "RETURNED", "Returned for clarification"
    DECLINED = "DECLINED", "Declined"
    CANCELLED = "CANCELLED", "Cancelled"


# Fields a sender may choose to share. Everything else stays with the case team.
SHAREABLE_FIELDS = {
    "age_range": "Age range",
    "preferred_language": "Preferred language",
    "incident_category": "General incident category",
    "district": "District",
    "immediate_risk": "Immediate protection risk flag",
    "protection_concerns": "Protection concerns (sensitive)",
    "location_detail": "Location detail (sensitive)",
}


class Referral(TimeStampedModel):
    reference = models.CharField(max_length=20, unique=True)
    case = models.ForeignKey("cases.ChildCase", on_delete=models.CASCADE, related_name="referrals")
    sending_institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="sent_referrals")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    receiving_institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="received_referrals")
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_referrals"
    )
    category = models.CharField(max_length=20, choices=ReferralCategory.choices, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    purpose = models.CharField(max_length=500, help_text="Why the referral is made and what is requested.")
    shared_fields = models.JSONField(default=list)
    shared_data = models.JSONField(default=dict, help_text="Snapshot of only the authorised fields.")
    status = models.CharField(max_length=15, choices=ReferralStatus.choices, default=ReferralStatus.DRAFT, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome_summary = models.CharField(
        max_length=500, blank=True, help_text="Non-clinical summary shared back with the sender."
    )
    restricted_notes = EncryptedTextField(blank=True, help_text="Visible to the receiving institution only.")
    visible_to_beneficiary = models.BooleanField(
        default=False, help_text="Show the service type (not details) in the beneficiary portal."
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["receiving_institution", "status"]), models.Index(fields=["sending_institution", "status"])]

    def __str__(self):
        return self.reference


class ReferralStatusHistory(TimeStampedModel):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=15, blank=True)
    to_status = models.CharField(max_length=15)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="+")
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["created_at"]
