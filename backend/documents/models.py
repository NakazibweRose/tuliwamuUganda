"""Case documents (medical reports, police files, court papers …) with need-to-know sharing.

Access model:
* The uploading institution always has access.
* A document attached to a referral is shared with the other party of that referral only.
* Further sharing ("forwarding", e.g. police → ODPP) is an explicit, audited DocumentAccess row, and only
  possible when the uploader allowed onward sharing.
* Complainants, caregivers, children and administrators never have access.
* File bytes are Fernet-encrypted in the database; every download is audited.
"""
from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class DocumentCategory(models.TextChoices):
    MEDICAL_REPORT = "MEDICAL_REPORT", "Medical report"
    MEDICAL_FORM = "MEDICAL_FORM", "Medical examination form (e.g. PF3)"
    FORENSIC_REPORT = "FORENSIC_REPORT", "Forensic report"
    POLICE_FILE = "POLICE_FILE", "Police case file"
    STATEMENT = "STATEMENT", "Statement"
    PROSECUTION_DOCUMENT = "PROSECUTION_DOCUMENT", "Prosecution document"
    COURT_DOCUMENT = "COURT_DOCUMENT", "Court document"
    WELFARE_REPORT = "WELFARE_REPORT", "Social welfare / probation report"
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT", "Legal aid document"
    OTHER = "OTHER", "Other"


class CaseDocument(TimeStampedModel):
    case = models.ForeignKey("cases.ChildCase", on_delete=models.CASCADE, related_name="documents")
    referral = models.ForeignKey("referrals.Referral", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents",
                                 help_text="Referral the document was uploaded on (shares it with the other party).")
    institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT, related_name="documents",
                                    help_text="Uploading (owning) institution.")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    category = models.CharField(max_length=24, choices=DocumentCategory.choices)
    title = models.CharField(max_length=150)
    filename = models.CharField(max_length=150)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    data = models.BinaryField(help_text="Fernet-encrypted file bytes.")
    forwardable = models.BooleanField(default=True, help_text="Recipients may share it onward with other case institutions.")
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    withdraw_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["case", "institution"])]

    def __str__(self):
        return self.title


class DocumentAccess(TimeStampedModel):
    document = models.ForeignKey(CaseDocument, on_delete=models.CASCADE, related_name="access")
    institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT, related_name="+")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    via_referral = models.ForeignKey("referrals.Referral", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reason = models.CharField(max_length=40, default="REFERRAL")  # REFERRAL | FORWARDED

    class Meta:
        constraints = [models.UniqueConstraint(fields=["document", "institution"], name="uniq_document_access")]
