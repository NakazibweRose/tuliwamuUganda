from accounts.models import User
from accounts.roles import ANONYMOUS_REPORT_TRIAGE_ROLES
from notifications.services import notify


def alert_triage_officers(report):
    """Discreetly alert police supervisors that a new unverified anonymous report arrived."""
    officers = User.objects.filter(
        role__in=ANONYMOUS_REPORT_TRIAGE_ROLES, is_active=True,
        memberships__is_active=True, memberships__is_supervisor=True,
    ).distinct()
    for officer in officers:
        notify(officer, "ANONYMOUS_REPORT", link=f"/app/anonymous-reports/{report.id}", dedup_key=f"anon:{report.id}")
