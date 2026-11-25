import hashlib
import io
import re
import zipfile

from cryptography.fernet import InvalidToken
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.services import record
from cases import access
from cases.models import CaseAssignment
from core.fields import _fernet
from notifications.services import notify_institution
from referrals.models import Referral, ReferralStatus

from .models import CaseDocument, DocumentAccess

MAX_BYTES = 10 * 1024 * 1024
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_type(head, raw):
    """Identify the file from its content (never trust the browser's name or type)."""
    if head.startswith(b"%PDF-"):
        return "application/pdf", "pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", "webp"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names = z.namelist()
            if "word/document.xml" in names and not any(n.startswith("word/vbaProject") for n in names):
                return DOCX, "docx"
        except zipfile.BadZipFile:
            pass
    return None, None


def safe_filename(name, ext):
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", (name or "document").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]).strip(" ._") or "document"
    base = base.rsplit(".", 1)[0][:100]
    return f"{base}.{ext}"


def visible_documents(user):
    inst = access.user_institution(user)
    if inst is None:
        return CaseDocument.objects.none()
    return CaseDocument.objects.filter(withdrawn_at__isnull=True).filter(
        Q(institution=inst) | Q(access__institution=inst)
    ).distinct().select_related("institution", "uploaded_by", "referral", "case")


def related_institutions(case):
    """Institutions legitimately involved in a case: the case team and every referral party."""
    ids = set(CaseAssignment.objects.filter(case=case, is_active=True).values_list("institution_id", flat=True))
    for s, r in Referral.objects.filter(case=case).exclude(status__in=[ReferralStatus.DRAFT, ReferralStatus.CANCELLED]).values_list(
            "sending_institution_id", "receiving_institution_id"):
        ids.update([s, r])
    return ids


def _counterpart(referral, inst):
    if referral.sending_institution_id == inst.id:
        return referral.receiving_institution
    if referral.receiving_institution_id == inst.id:
        return referral.sending_institution
    return None


@transaction.atomic
def upload(user, case, upload_file, category, title, referral=None, forwardable=True, request=None):
    inst = access.user_institution(user)
    if inst is None:
        raise PermissionDenied("Only institutional staff can upload documents.")
    counterpart = None
    if referral is not None:
        if referral.case_id != case.id:
            raise ValidationError({"referral_id": ["This referral belongs to another case."]})
        counterpart = _counterpart(referral, inst)
        if counterpart is None or referral.status in {ReferralStatus.DRAFT, ReferralStatus.CANCELLED}:
            raise PermissionDenied("Your institution cannot attach documents to this referral.")
    elif not access.is_on_team(user, case):
        raise PermissionDenied("You are not on this case team.")
    if upload_file is None:
        raise ValidationError({"file": ["Choose a file."]})
    if upload_file.size > MAX_BYTES:
        raise ValidationError({"file": ["Files must be 10 MB or smaller."]})
    raw = upload_file.read()
    mime, ext = detect_type(raw[:16], raw)
    if mime is None:
        raise ValidationError({"file": ["Only PDF, JPG, PNG, WEBP or Word (.docx) files are accepted."]})
    doc = CaseDocument.objects.create(
        case=case, referral=referral, institution=inst, uploaded_by=user, category=category,
        title=(title or "").strip()[:150] or safe_filename(upload_file.name, ext),
        filename=safe_filename(upload_file.name, ext), mime_type=mime, size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(), data=_fernet().encrypt(raw), forwardable=forwardable,
    )
    if counterpart is not None:
        DocumentAccess.objects.create(document=doc, institution=counterpart, granted_by=user, via_referral=referral, reason="REFERRAL")
        notify_institution(counterpart, "DOCUMENT_SHARED", link=f"/app/referrals/{referral.id}", dedup_key=f"doc:{doc.id}")
    record(user, "document.upload", doc, request=request, case_id=str(case.id), category=category,
           referral_id=str(referral.id) if referral else "", shared_with=str(counterpart.id) if counterpart else "")
    return doc


def can_read(user, doc):
    return visible_documents(user).filter(pk=doc.pk).exists()


def decrypt(doc):
    try:
        return _fernet().decrypt(bytes(doc.data))
    except InvalidToken:
        return None


def share_targets(user, doc):
    from institutions.models import Institution

    inst = access.user_institution(user)
    if inst is None or not can_read(user, doc) or not (doc.forwardable or doc.institution_id == inst.id):
        return Institution.objects.none()
    already = set(doc.access.values_list("institution_id", flat=True)) | {doc.institution_id}
    return Institution.objects.filter(id__in=related_institutions(doc.case) - already, is_active=True)


@transaction.atomic
def share(user, doc, target, request=None):
    inst = access.user_institution(user)
    if not can_read(user, doc):
        raise PermissionDenied()
    if doc.institution_id != inst.id and not doc.forwardable:
        raise PermissionDenied("The uploading institution did not allow this document to be forwarded.")
    if target.id not in related_institutions(doc.case):
        raise ValidationError({"institution_id": ["Documents can only be shared with institutions involved in this case."]})
    # Link the forwarded copy to the referral between the two institutions, so it shows on that referral.
    via = Referral.objects.filter(case=doc.case).exclude(status__in=[ReferralStatus.DRAFT, ReferralStatus.CANCELLED]).filter(
        Q(sending_institution=inst, receiving_institution=target) | Q(sending_institution=target, receiving_institution=inst)
    ).order_by("-created_at").first()
    grant, created = DocumentAccess.objects.get_or_create(
        document=doc, institution=target, defaults={"granted_by": user, "reason": "FORWARDED", "via_referral": via})
    if created:
        notify_institution(target, "DOCUMENT_SHARED", link=f"/app/cases/{doc.case_id}?tab=documents", dedup_key=f"doc:{doc.id}:{target.id}")
    record(user, "document.share", doc, request=request, case_id=str(doc.case_id), shared_with=str(target.id), security=True)
    return grant


@transaction.atomic
def withdraw(user, doc, reason, request=None):
    inst = access.user_institution(user)
    if inst is None or doc.institution_id != inst.id:
        raise PermissionDenied("Only the uploading institution can withdraw a document.")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Give a reason (e.g. uploaded to the wrong case)."]})
    doc.withdrawn_at = timezone.now()
    doc.withdrawn_by = user
    doc.withdraw_reason = reason.strip()[:300]
    doc.data = b""  # the content itself is destroyed; metadata stays for the audit trail
    doc.save(update_fields=["withdrawn_at", "withdrawn_by", "withdraw_reason", "data", "updated_at"])
    record(user, "document.withdraw", doc, request=request, case_id=str(doc.case_id), security=True)
    return doc
