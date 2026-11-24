from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField
from core.models import TimeStampedModel
from institutions.models import Institution, Region


class AgeRange(models.TextChoices):
    A0_4 = "0-4", "0–4 years"
    A5_8 = "5-8", "5–8 years"
    A9_11 = "9-11", "9–11 years"
    A12_14 = "12-14", "12–14 years"
    A15_17 = "15-17", "15–17 years"
    UNKNOWN = "UNKNOWN", "Not known"


# Age bands for which a child may be given their own (safeguarded) portal access.
SELF_ACCESS_AGE_RANGES = {AgeRange.A12_14, AgeRange.A15_17}


class IncidentCategory(models.TextChoices):
    SEXUAL_ABUSE = "SEXUAL_ABUSE", "Sexual abuse / defilement"
    PHYSICAL_VIOLENCE = "PHYSICAL_VIOLENCE", "Physical violence"
    NEGLECT = "NEGLECT", "Neglect"
    EXPLOITATION = "EXPLOITATION", "Exploitation / child labour"
    TRAFFICKING = "TRAFFICKING", "Trafficking"
    EMOTIONAL_ABUSE = "EMOTIONAL_ABUSE", "Emotional / psychological abuse"
    OTHER = "OTHER", "Other"


class Child(TimeStampedModel):
    """A protected child. Deliberately holds no legal name: only a pseudonym used inside the platform."""

    pseudonym = models.CharField(max_length=60, help_text='e.g. "Demo Child A". Never a real name in demos.')
    age_range = models.CharField(max_length=8, choices=AgeRange.choices, default=AgeRange.UNKNOWN)
    preferred_language = models.CharField(max_length=5, default="en")
    registered_by_institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="+")

    def __str__(self):
        return self.pseudonym


class JourneyStep(models.TextChoices):
    REPORTED = "REPORTED", "Reported"
    SUPPORT = "SUPPORT", "Care & support"
    INVESTIGATION = "INVESTIGATION", "Investigation"
    PROSECUTION = "PROSECUTION", "Prosecution review"
    COURT = "COURT", "Court"
    CONCLUDED = "CONCLUDED", "Concluded"


class CaseStage(models.Model):
    """Configurable case lifecycle stage. Not every case passes through every stage."""

    code = models.CharField(max_length=40, primary_key=True)
    label = models.CharField(max_length=120)
    beneficiary_label = models.CharField(max_length=200, help_text="Plain-language English text (translated in the UI).")
    journey_step = models.CharField(max_length=20, choices=JourneyStep.choices)
    order = models.PositiveIntegerField()
    allowed_roles = models.JSONField(default=list, help_text="Roles that may move a case into this stage.")
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class ChildCase(TimeStampedModel):
    reference = models.CharField(max_length=20, unique=True)
    child = models.ForeignKey(Child, on_delete=models.PROTECT, related_name="cases")
    date_reported = models.DateField()
    lead_institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="led_cases")
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_cases"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    external_reference = models.CharField(
        max_length=60, blank=True, help_text="Reference in the institution's own system (fictional in demos)."
    )
    incident_category = models.CharField(max_length=30, choices=IncidentCategory.choices, db_index=True)
    district = models.CharField(max_length=80)
    region = models.CharField(max_length=10, choices=Region.choices, db_index=True)
    location_detail = EncryptedTextField(blank=True, help_text="Restricted: lead institution only.")
    protection_concerns = EncryptedTextField(blank=True, help_text="Restricted: lead institution only.")
    immediate_risk = models.BooleanField(default=False)
    referral_needs = models.JSONField(default=list, blank=True, help_text="Referral categories identified at intake.")
    stage = models.ForeignKey(CaseStage, on_delete=models.PROTECT, related_name="cases")
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead_institution", "stage"]), models.Index(fields=["date_reported"])]
        constraints = [
            models.UniqueConstraint(
                fields=["lead_institution", "external_reference"],
                condition=~models.Q(external_reference=""),
                name="uniq_external_ref_per_institution",
            )
        ]

    def __str__(self):
        return self.reference


class CaseAssignment(TimeStampedModel):
    """Institutions on the case team. The lead institution always has an active assignment."""

    case = models.ForeignKey(ChildCase, on_delete=models.CASCADE, related_name="assignments")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="case_assignments")
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    role_in_case = models.CharField(max_length=30)
    is_lead = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "institution"], name="uniq_case_institution")]


class CaseStatusHistory(TimeStampedModel):
    case = models.ForeignKey(ChildCase, on_delete=models.CASCADE, related_name="status_history")
    from_stage = models.ForeignKey(CaseStage, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    to_stage = models.ForeignKey(CaseStage, on_delete=models.PROTECT, related_name="+")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="+")
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["created_at"]


class Visibility(models.TextChoices):
    INTERNAL = "INTERNAL", "Own institution only"
    CASE_TEAM = "CASE_TEAM", "All institutions on the case team"


class BeneficiaryStatus(models.TextChoices):
    NONE = "NONE", "Not for beneficiary"
    PENDING = "PENDING", "Awaiting review"
    APPROVED = "APPROVED", "Approved for beneficiary"
    REJECTED = "REJECTED", "Rejected"


class UpdateCategory(models.TextChoices):
    REGISTRATION = "REGISTRATION", "Registration"
    STAGE_CHANGE = "STAGE_CHANGE", "Stage change"
    REFERRAL = "REFERRAL", "Referral"
    INVESTIGATION = "INVESTIGATION", "Investigation"
    MEDICAL = "MEDICAL", "Medical"
    FORENSIC = "FORENSIC", "Forensic"
    PROSECUTION = "PROSECUTION", "Prosecution"
    COURT = "COURT", "Court"
    WELFARE = "WELFARE", "Welfare"
    SUPPORT = "SUPPORT", "Support"
    APPOINTMENT = "APPOINTMENT", "Appointment"
    GENERAL = "GENERAL", "General"


class CaseUpdate(TimeStampedModel):
    """A timeline entry. Institutional notes never become beneficiary-visible on their own:
    the optional beneficiary_message must be approved by an authorised officer who is not its author."""

    case = models.ForeignKey(ChildCase, on_delete=models.CASCADE, related_name="updates")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="+")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    category = models.CharField(max_length=20, choices=UpdateCategory.choices, default=UpdateCategory.GENERAL)
    note = models.TextField(blank=True)
    visibility = models.CharField(max_length=12, choices=Visibility.choices, default=Visibility.CASE_TEAM)
    beneficiary_message = models.CharField(max_length=400, blank=True)
    beneficiary_journey_step = models.CharField(max_length=20, choices=JourneyStep.choices, blank=True)
    beneficiary_status = models.CharField(max_length=10, choices=BeneficiaryStatus.choices, default=BeneficiaryStatus.NONE)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    system_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["case", "beneficiary_status"])]


class FollowUpStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DONE = "DONE", "Done"
    CANCELLED = "CANCELLED", "Cancelled"


class FollowUp(TimeStampedModel):
    case = models.ForeignKey(ChildCase, on_delete=models.CASCADE, related_name="follow_ups")
    referral = models.ForeignKey("referrals.Referral", on_delete=models.SET_NULL, null=True, blank=True, related_name="follow_ups")
    assistance_request = models.ForeignKey(
        "support_services.AssistanceRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="follow_ups"
    )
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="+")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="follow_ups")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    description = models.CharField(max_length=300)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING, db_index=True)
    outcome_note = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_date"]


class Relationship(models.TextChoices):
    SELF = "SELF", "The child themself"
    PARENT = "PARENT", "Parent"
    GUARDIAN = "GUARDIAN", "Legal guardian"
    CAREGIVER = "CAREGIVER", "Other caregiver"
    SOCIAL_WORKER_PROXY = "SOCIAL_WORKER_PROXY", "Social worker acting as proxy"


class GrantStatus(models.TextChoices):
    PENDING = "PENDING", "Awaiting second-officer approval"
    ACTIVE = "ACTIVE", "Active"
    REVOKED = "REVOKED", "Revoked"


class BeneficiaryAccessGrant(TimeStampedModel):
    """Explicit, per-case permission for a child or caregiver account to view approved updates.

    Never created automatically. Requires a written basis, a confirmed conflict-of-interest check
    and approval by a second officer (four-eyes rule)."""

    case = models.ForeignKey(ChildCase, on_delete=models.CASCADE, related_name="access_grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_grants")
    relationship = models.CharField(max_length=24, choices=Relationship.choices)
    basis = models.CharField(max_length=500, help_text="Why access is in the child's best interests.")
    conflict_check_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=GrantStatus.choices, default=GrantStatus.PENDING, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "user"], condition=~models.Q(status="REVOKED"), name="uniq_live_grant_per_case_user"
            )
        ]
