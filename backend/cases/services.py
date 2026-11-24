"""Case workflow operations. Views call these; each runs in a transaction and writes history + audit."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.services import record
from core.references import unique_reference
from notifications.services import notify, notify_institution

from . import access
from .models import (
    BeneficiaryAccessGrant,
    BeneficiaryStatus,
    CaseAssignment,
    CaseStage,
    CaseStatusHistory,
    CaseUpdate,
    Child,
    ChildCase,
    GrantStatus,
    Relationship,
    SELF_ACCESS_AGE_RANGES,
    UpdateCategory,
    Visibility,
)

INITIAL_STAGE = "REPORT_RECEIVED"
DUPLICATE_WINDOW_DAYS = 14


def find_possible_duplicates(institution, child, incident_category, date_reported):
    if child is None:
        return ChildCase.objects.none()
    window = timedelta(days=DUPLICATE_WINDOW_DAYS)
    return ChildCase.objects.filter(
        lead_institution=institution,
        child=child,
        incident_category=incident_category,
        date_reported__gte=date_reported - window,
        date_reported__lte=date_reported + window,
    )


def generate_case_reference():
    year = timezone.localdate().year
    return unique_reference(ChildCase, "reference", f"TLW-{year}", length=6)


@transaction.atomic
def register_case(user, data, request=None):
    institution = access.user_institution(user)
    if institution is None:
        raise PermissionDenied("You must belong to an active institution to register a case.")

    child = data.get("child")
    if child is not None and not access.team_cases(user).filter(child=child).exists():
        # Linking to an existing child is only allowed if the user's institution already works with that child.
        raise ValidationError({"child_id": ["Unknown child record."]})
    if child is None:
        child = Child.objects.create(
            pseudonym=data["child_pseudonym"],
            age_range=data["age_range"],
            preferred_language=data.get("preferred_language", "en"),
            registered_by_institution=institution,
        )

    if not data.get("confirm_not_duplicate"):
        dupes = find_possible_duplicates(institution, child, data["incident_category"], data["date_reported"])
        if dupes.exists():
            raise ValidationError(
                {
                    "duplicate_warning": [
                        "A case for this child with the same category was registered within "
                        f"{DUPLICATE_WINDOW_DAYS} days: " + ", ".join(dupes.values_list("reference", flat=True))
                        + ". Confirm it is not a duplicate to continue."
                    ]
                }
            )

    officer = data.get("assigned_officer") or user
    if officer.institution != institution:
        raise ValidationError({"assigned_officer_id": ["The assigned officer must belong to your institution."]})

    stage = CaseStage.objects.get(code=INITIAL_STAGE)
    case = ChildCase.objects.create(
        reference=generate_case_reference(),
        child=child,
        date_reported=data["date_reported"],
        lead_institution=institution,
        assigned_officer=officer,
        created_by=user,
        external_reference=data.get("external_reference", ""),
        incident_category=data["incident_category"],
        district=data["district"],
        region=data["region"],
        location_detail=data.get("location_detail", ""),
        protection_concerns=data.get("protection_concerns", ""),
        immediate_risk=data.get("immediate_risk", False),
        referral_needs=data.get("referral_needs", []),
        stage=stage,
    )
    CaseAssignment.objects.create(
        case=case, institution=institution, officer=officer, role_in_case="LEAD", is_lead=True, assigned_by=user
    )
    CaseStatusHistory.objects.create(case=case, to_stage=stage, changed_by=user, institution=institution, note="Case registered")
    CaseUpdate.objects.create(
        case=case,
        institution=institution,
        author=user,
        category=UpdateCategory.REGISTRATION,
        note="Case registered.",
        visibility=Visibility.CASE_TEAM,
        beneficiary_message="Your report was received and a case has been opened.",
        beneficiary_journey_step="REPORTED",
        beneficiary_status=BeneficiaryStatus.APPROVED,
        reviewed_by=user,
        reviewed_at=timezone.now(),
        system_generated=True,
    )
    if officer != user:
        notify(officer, "FOLLOW_UP_DUE", link=f"/app/cases/{case.id}", dedup_key=f"case-assigned:{case.id}")
    record(user, "case.create", case, request=request, immediate_risk=case.immediate_risk)
    return case


@transaction.atomic
def change_stage(user, case, stage_code, note="", request=None):
    try:
        stage = CaseStage.objects.get(code=stage_code, is_active=True)
    except CaseStage.DoesNotExist:
        raise ValidationError({"stage": ["Unknown stage."]})
    if not access.can_set_stage(user, case, stage):
        record(user, "case.change_stage", case, request=request, success=False, security=True, stage=stage_code)
        raise PermissionDenied("Your role cannot move a case into this stage.")
    if case.stage_id == stage.code:
        raise ValidationError({"stage": ["The case is already at this stage."]})
    previous = case.stage
    case.stage = stage
    case.closed_at = timezone.now() if stage.is_terminal else None
    case.save(update_fields=["stage", "closed_at", "updated_at"])
    CaseStatusHistory.objects.create(
        case=case, from_stage=previous, to_stage=stage, changed_by=user, institution=user.institution, note=note[:500]
    )
    CaseUpdate.objects.create(
        case=case,
        institution=user.institution,
        author=user,
        category=UpdateCategory.STAGE_CHANGE,
        note=f"Stage changed from “{previous.label}” to “{stage.label}”." + (f" {note}" if note else ""),
        visibility=Visibility.CASE_TEAM,
        system_generated=True,
    )
    record(user, "case.change_stage", case, request=request, from_stage=previous.code, to_stage=stage.code)
    return case


def _notify_reviewers(case, exclude=None, dedup=""):
    """Tell people who can approve beneficiary content that something is waiting."""
    notify_institution(
        case.lead_institution, "UPDATE_NEEDS_REVIEW", link=f"/app/cases/{case.id}", dedup_key=dedup, exclude=exclude
    )


@transaction.atomic
def add_update(user, case, data, request=None):
    if not access.is_on_team(user, case):
        raise PermissionDenied("You are not on this case team.")
    message = (data.get("beneficiary_message") or "").strip()
    update = CaseUpdate.objects.create(
        case=case,
        institution=user.institution,
        author=user,
        category=data.get("category", UpdateCategory.GENERAL),
        note=data.get("note", ""),
        visibility=data.get("visibility", Visibility.CASE_TEAM),
        beneficiary_message=message,
        beneficiary_journey_step=data.get("beneficiary_journey_step", "") if message else "",
        beneficiary_status=BeneficiaryStatus.PENDING if message else BeneficiaryStatus.NONE,
    )
    if message:
        _notify_reviewers(case, exclude=user, dedup=f"update-review:{update.id}")
    record(user, "case.add_update", update, request=request, case_id=str(case.id), proposes_beneficiary_message=bool(message))
    return update


@transaction.atomic
def review_update(user, update, approve, edited_message=None, request=None):
    case = update.case
    if update.beneficiary_status != BeneficiaryStatus.PENDING:
        raise ValidationError({"detail": ["This update is not awaiting review."]})
    if not access.can_review_beneficiary_content(user, case):
        raise PermissionDenied("You cannot review family-facing updates for this case.")
    if update.author_id == user.id:
        raise PermissionDenied("A different officer must review an update you wrote.")
    if edited_message:
        update.beneficiary_message = edited_message.strip()[:400]
    update.beneficiary_status = BeneficiaryStatus.APPROVED if approve else BeneficiaryStatus.REJECTED
    update.reviewed_by = user
    update.reviewed_at = timezone.now()
    update.save()
    if approve:
        for grant in BeneficiaryAccessGrant.objects.filter(case=case, status=GrantStatus.ACTIVE).select_related("user"):
            notify(grant.user, "CASE_UPDATE", link=f"/me/cases/{case.id}", dedup_key=f"ben-update:{update.id}")
    record(user, "case.review_update", update, request=request, approved=approve)
    return update


def propose_system_beneficiary_update(case, institution, author, message, journey_step, category):
    """System-generated proposal (e.g. after a referral completes). Still needs human approval."""
    update = CaseUpdate.objects.create(
        case=case,
        institution=institution,
        author=author,
        category=category,
        note="Proposed family-facing update generated from a referral milestone.",
        visibility=Visibility.CASE_TEAM,
        beneficiary_message=message,
        beneficiary_journey_step=journey_step,
        beneficiary_status=BeneficiaryStatus.PENDING,
        system_generated=True,
    )
    _notify_reviewers(case, exclude=None, dedup=f"update-review:{update.id}")
    return update


# ---------- Beneficiary access grants ----------

@transaction.atomic
def create_grant(user, case, grant_user, data, request=None):
    from accounts.roles import Role

    if not access.can_manage_grants(user, case):
        raise PermissionDenied("You cannot manage portal access for this case.")
    if grant_user.role not in {Role.BENEFICIARY, Role.CAREGIVER}:
        raise ValidationError({"user_id": ["Access can only be granted to child or caregiver accounts."]})
    relationship = data["relationship"]
    if (relationship == Relationship.SELF) != (grant_user.role == Role.BENEFICIARY):
        raise ValidationError({"relationship": ["Use 'The child themself' only for a child's own account."]})
    if relationship == Relationship.SELF and case.child.age_range not in SELF_ACCESS_AGE_RANGES:
        raise ValidationError({"relationship": ["Direct access for a child is only allowed from age 12, with safeguards."]})
    if not data.get("conflict_check_confirmed"):
        raise ValidationError(
            {"conflict_check_confirmed": ["Confirm that this person is not implicated in the allegation and access is in the child's best interests."]}
        )
    if BeneficiaryAccessGrant.objects.filter(case=case, user=grant_user).exclude(status=GrantStatus.REVOKED).exists():
        raise ValidationError({"user_id": ["This person already has a pending or active grant for this case."]})
    grant = BeneficiaryAccessGrant.objects.create(
        case=case,
        user=grant_user,
        relationship=relationship,
        basis=data["basis"],
        conflict_check_confirmed=True,
        valid_until=data.get("valid_until"),
        created_by=user,
    )
    notify_institution(
        case.lead_institution, "GRANT_NEEDS_APPROVAL", link=f"/app/cases/{case.id}", dedup_key=f"grant:{grant.id}", exclude=user
    )
    record(user, "grant.create", grant, request=request, case_id=str(case.id), relationship=relationship)
    return grant


@transaction.atomic
def approve_grant(user, grant, request=None):
    if grant.status != GrantStatus.PENDING:
        raise ValidationError({"detail": ["This grant is not awaiting approval."]})
    if not access.can_manage_grants(user, grant.case):
        raise PermissionDenied("You cannot approve portal access for this case.")
    if grant.created_by_id == user.id:
        raise PermissionDenied("A second officer must approve access that you requested.")
    grant.status = GrantStatus.ACTIVE
    grant.approved_by = user
    grant.approved_at = timezone.now()
    grant.save()
    record(user, "grant.approve", grant, request=request, case_id=str(grant.case_id))
    return grant


@transaction.atomic
def revoke_grant(user, grant, reason, request=None):
    if grant.status == GrantStatus.REVOKED:
        raise ValidationError({"detail": ["Already revoked."]})
    if not access.can_manage_grants(user, grant.case):
        raise PermissionDenied("You cannot change portal access for this case.")
    grant.status = GrantStatus.REVOKED
    grant.revoked_by = user
    grant.revoked_at = timezone.now()
    grant.revoke_reason = reason[:300]
    grant.save()
    record(user, "grant.revoke", grant, request=request, case_id=str(grant.case_id), security=True)
    return grant
