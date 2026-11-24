"""Central, backend-enforced access rules for case data.

Rules (see docs/01-phase1-architecture.md §4):
* A user sees a case only if their institution is on the case team (active CaseAssignment).
* Sensitive case fields are visible only to the lead institution.
* Receiving institutions join the case team when they acknowledge a referral; before that they
  see only the referral snapshot.
* Beneficiary/caregiver accounts see only cases with an ACTIVE grant, and only approved content.
* Administrators have no case-content access.
"""
from django.db.models import Q
from django.utils import timezone

from accounts.roles import INSTITUTIONAL_ROLES, Role

from .models import BeneficiaryAccessGrant, ChildCase, GrantStatus


def user_institution(user):
    if not (user and user.is_authenticated and user.role in INSTITUTIONAL_ROLES):
        return None
    return user.institution


def team_cases(user):
    inst = user_institution(user)
    if inst is None:
        return ChildCase.objects.none()
    return ChildCase.objects.filter(assignments__institution=inst, assignments__is_active=True).distinct()


def is_on_team(user, case):
    inst = user_institution(user)
    return bool(inst) and case.assignments.filter(institution=inst, is_active=True).exists()


def is_lead(user, case):
    inst = user_institution(user)
    return bool(inst) and case.lead_institution_id == inst.id


def can_view_sensitive(user, case):
    return is_lead(user, case)


def can_review_beneficiary_content(user, case):
    """Lead institution officers, or probation/social welfare officers on the case team."""
    if is_lead(user, case):
        return True
    return user.role == Role.PROBATION and is_on_team(user, case)


def can_manage_grants(user, case):
    return user.role in {Role.POLICE, Role.PROBATION} and can_review_beneficiary_content(user, case)


def can_set_stage(user, case, stage):
    return is_on_team(user, case) and user.role in (stage.allowed_roles or [])


def active_grants(user):
    today = timezone.localdate()
    return BeneficiaryAccessGrant.objects.filter(user=user, status=GrantStatus.ACTIVE).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )


def beneficiary_cases(user):
    return ChildCase.objects.filter(id__in=active_grants(user).values("case_id"))
