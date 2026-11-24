from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class InstitutionType(models.TextChoices):
    POLICE = "POLICE", "Police"
    HEALTH = "HEALTH", "Health facility"
    FORENSIC = "FORENSIC", "Forensic services"
    ODPP = "ODPP", "Office of the DPP"
    COURT = "COURT", "Court registry"
    PROBATION = "PROBATION", "Probation & social welfare"
    LEGAL_AID = "LEGAL_AID", "Legal aid provider"
    PSYCHOSOCIAL = "PSYCHOSOCIAL", "Psychosocial support"
    SHELTER = "SHELTER", "Protection & shelter"


class Region(models.TextChoices):
    CENTRAL = "CENTRAL", "Central"
    EASTERN = "EASTERN", "Eastern"
    NORTHERN = "NORTHERN", "Northern"
    WESTERN = "WESTERN", "Western"


class Institution(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=20, choices=InstitutionType.choices, db_index=True)
    district = models.CharField(max_length=80)
    region = models.CharField(max_length=10, choices=Region.choices)
    public_contact = models.CharField(max_length=120, blank=True, help_text="Institutional (not personal) contact.")
    is_demo = models.BooleanField(default=True, help_text="Fictional institution used for demonstration.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstitutionMembership(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="memberships")
    title = models.CharField(max_length=120, blank=True)
    is_supervisor = models.BooleanField(default=False, help_text="May view aggregate analytics.")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "institution"], name="uniq_membership")]

    def __str__(self):
        return f"{self.user} @ {self.institution}"
