"""Referral state machine. Every transition is validated, timestamped, stored in history and audited."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.services import record
from cases import access
from cases.models import CaseAssignment, CaseUpdate, UpdateCategory, Visibility
from cases.services import propose_system_beneficiary_update
from core.references import unique_reference
from notifications.services import notify, notify_institution
from translations.catalog import t

from .models import CATEGORY_RECEIVER_TYPES, SHAREABLE_FIELDS, Referral, ReferralStatus, ReferralStatusHistory

S = ReferralStatus

# action -> (allowed from-states, to-state, side: "sender" | "receiver")
TRANSITIONS = {
    "send": ({S.DRAFT}, S.SENT, "sender"),
    "cancel": ({S.DRAFT, S.SENT, S.RETURNED}, S.CANCELLED, "sender"),
    "resend": ({S.RETURNED}, S.SENT, "sender"),
    "acknowledge": ({S.SENT}, S.ACKNOWLEDGED, "receiver"),
    "decline": ({S.SENT}, S.DECLINED, "receiver"),
    "start": ({S.ACKNOWLEDGED}, S.IN_PROGRESS, "receiver"),
    "complete": ({S.ACKNOWLEDGED, S.IN_PROGRESS}, S.COMPLETED, "receiver"),
    "return": ({S.SENT, S.ACKNOWLEDGED, S.IN_PROGRESS}, S.RETURNED, "receiver"),
}
NOTE_REQUIRED = {"decline", "return", "cancel", "resend"}
JOURNEY_FOR_CATEGORY = {
    "MEDICAL": "SUPPORT", "PSYCHOSOCIAL": "SUPPORT", "LEGAL_AID": "SUPPORT", "SHELTER": "SUPPORT",
    "PROBATION": "SUPPORT", "FORENSIC": "INVESTIGATION", "PROSECUTION": "PROSECUTION", "COURT": "COURT",
}
UPDATE_CATEGORY = {
    "MEDICAL": UpdateCategory.MEDICAL, "FORENSIC": UpdateCategory.FORENSIC, "PROSECUTION": UpdateCategory.PROSECUTION,
    "COURT": UpdateCategory.COURT, "PROBATION": UpdateCategory.WELFARE,
}


def visible_referrals(user):
    inst = access.user_institution(user)
    if inst is None:
        return Referral.objects.none()
    from django.db.models import Q

    return Referral.objects.filter(
        Q(sending_institution=inst) | (Q(receiving_institution=inst) & ~Q(status=S.DRAFT))
    ).select_related("case", "sending_institution", "receiving_institution", "sent_by", "assigned_officer")


def snapshot(case, fields):
    data = {}
    for f in fields:
        if f == "age_range":
            data[f] = case.child.age_range
        elif f == "preferred_language":
            data[f] = case.child.preferred_language
        else:
            data[f] = getattr(case, f)
    return data


@transaction.atomic
def create_referral(user, case, data, request=None):
    if not access.is_on_team(user, case):
        raise PermissionDenied("You are not on this case team.")
    receiver = data["receiving_institution"]
    category = data["category"]
    if receiver.id == user.institution.id:
        raise ValidationError({"receiving_institution_id": ["You cannot refer a case to your own institution."]})
    if not receiver.is_active or receiver.type not in CATEGORY_RECEIVER_TYPES.get(category, set()):
        raise ValidationError({"receiving_institution_id": ["This institution does not receive this type of referral."]})
    fields = list(dict.fromkeys(data.get("shared_fields") or []))
    unknown = [f for f in fields if f not in SHAREABLE_FIELDS]
    if unknown:
        raise ValidationError({"shared_fields": [f"Not shareable: {', '.join(unknown)}"]})
    sensitive = {"protection_concerns", "location_detail"} & set(fields)
    if sensitive and not access.can_view_sensitive(user, case):
        raise PermissionDenied("Only the lead institution can share sensitive fields.")
    if Referral.objects.filter(
        case=case, receiving_institution=receiver, category=category,
        status__in=[S.DRAFT, S.SENT, S.ACKNOWLEDGED, S.IN_PROGRESS, S.RETURNED],
    ).exists():
        raise ValidationError({"detail": ["An open referral of this type to this institution already exists for this case."]})

    referral = Referral.objects.create(
        reference=unique_reference(Referral, "reference", "REF", length=6),
        case=case,
        sending_institution=user.institution,
        sent_by=user,
        receiving_institution=receiver,
        category=category,
        priority=data.get("priority", "ROUTINE"),
        purpose=data["purpose"],
        shared_fields=fields,
        shared_data=snapshot(case, fields),
        visible_to_beneficiary=data.get("visible_to_beneficiary", False),
    )
    ReferralStatusHistory.objects.create(
        referral=referral, from_status="", to_status=S.DRAFT, actor=user, institution=user.institution, note="Draft created"
    )
    record(user, "referral.create", referral, request=request, case_id=str(case.id), category=category, shared_fields=fields)
    if data.get("send_now", True):
        referral = transition(user, referral, "send", request=request)
    return referral


def _side_ok(user, referral, side):
    inst = access.user_institution(user)
    if inst is None:
        return False
    if side == "sender":
        return referral.sending_institution_id == inst.id
    return referral.receiving_institution_id == inst.id


@transaction.atomic
def transition(user, referral, action, *, note="", outcome_summary=None, restricted_notes=None, request=None):
    if action not in TRANSITIONS:
        raise ValidationError({"action": ["Unknown action."]})
    allowed_from, to_status, side = TRANSITIONS[action]
    referral = Referral.objects.select_for_update().get(pk=referral.pk)
    if not _side_ok(user, referral, side):
        record(user, f"referral.{action}", referral, request=request, success=False, security=True)
        raise PermissionDenied("Your institution cannot perform this action on this referral.")
    if referral.status not in allowed_from:
        raise ValidationError({"detail": [f"Cannot {action} a referral that is {referral.get_status_display().lower()}."]})
    if action in NOTE_REQUIRED and not note.strip():
        raise ValidationError({"note": ["Please give a short reason."]})
    if action == "complete" and not (outcome_summary or "").strip():
        raise ValidationError({"outcome_summary": ["Add a short, non-clinical completion summary for the referring institution."]})

    now = timezone.now()
    previous = referral.status
    referral.status = to_status
    if action in {"send", "resend"}:
        referral.sent_at = now
    if action == "acknowledge":
        referral.acknowledged_at = now
        referral.assigned_officer = referral.assigned_officer or user
    if action == "complete":
        referral.completed_at = now
        referral.outcome_summary = outcome_summary.strip()[:500]
    if restricted_notes is not None and side == "receiver":
        referral.restricted_notes = restricted_notes
    referral.save()
    ReferralStatusHistory.objects.create(
        referral=referral, from_status=previous, to_status=to_status, actor=user, institution=user.institution, note=note[:500]
    )
    record(user, f"referral.{action}", referral, request=request, from_status=previous, to_status=to_status)
    _side_effects(user, referral, action, previous)
    return referral


def _timeline(referral, user, text, visibility=Visibility.CASE_TEAM):
    CaseUpdate.objects.create(
        case=referral.case,
        institution=user.institution,
        author=user,
        category=UPDATE_CATEGORY.get(referral.category, UpdateCategory.REFERRAL),
        note=text,
        visibility=visibility,
        system_generated=True,
    )


def _side_effects(user, referral, action, previous=None):
    case = referral.case
    label = referral.get_category_display()
    link_receiver = f"/app/referrals/{referral.id}"
    if action in {"send", "resend"}:
        _timeline(referral, user, f"{label} referral {referral.reference} sent to {referral.receiving_institution.name}.")
        notify_institution(referral.receiving_institution, "REFERRAL_RECEIVED", link=link_receiver,
                           dedup_key=f"ref-sent:{referral.id}:{referral.sent_at.isoformat()}")
        msg_key = f"ben.referral_sent.{referral.category}"
        if referral.visible_to_beneficiary and action == "send" and t(msg_key) != msg_key:
            propose_system_beneficiary_update(case, user.institution, user, t(msg_key), JOURNEY_FOR_CATEGORY[referral.category],
                                              UPDATE_CATEGORY.get(referral.category, UpdateCategory.REFERRAL))
    elif action == "acknowledge":
        # The receiving institution joins the case team (scoped, non-lead access).
        CaseAssignment.objects.update_or_create(
            case=case, institution=referral.receiving_institution,
            defaults={"officer": user, "role_in_case": referral.category, "is_active": True, "assigned_by": user},
        )
        _timeline(referral, user, f"{label} referral {referral.reference} acknowledged by {referral.receiving_institution.name}.")
        notify(referral.sent_by, "REFERRAL_ACKNOWLEDGED", link=link_receiver, dedup_key=f"ref-ack:{referral.id}")
    elif action == "start":
        _timeline(referral, user, f"Work started on {label.lower()} referral {referral.reference}.")
    elif action == "complete":
        _timeline(referral, user, f"{label} referral {referral.reference} completed. Summary: {referral.outcome_summary}")
        notify(referral.sent_by, "SUPPORT_COMPLETED", link=link_receiver, dedup_key=f"ref-done:{referral.id}")
        msg_key = f"ben.referral_completed.{referral.category}"
        propose_system_beneficiary_update(case, user.institution, user, t(msg_key),
                                          JOURNEY_FOR_CATEGORY[referral.category],
                                          UPDATE_CATEGORY.get(referral.category, UpdateCategory.REFERRAL))
    elif action in {"return", "decline"}:
        verb = "returned for clarification" if action == "return" else "declined"
        _timeline(referral, user, f"{label} referral {referral.reference} {verb} by {referral.receiving_institution.name}.")
        notify(referral.sent_by, "REFERRAL_FOLLOW_UP", link=link_receiver, dedup_key=f"ref-{action}:{referral.id}:{timezone.now().timestamp()}")
    elif action == "cancel":
        _timeline(referral, user, f"{label} referral {referral.reference} cancelled.")
        if previous != S.DRAFT:
            notify_institution(referral.receiving_institution, "REFERRAL_UPDATED", link=link_receiver, dedup_key=f"ref-cancel:{referral.id}")
