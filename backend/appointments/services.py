from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.roles import Role
from audit.services import record
from cases import access
from cases.models import BeneficiaryAccessGrant, CaseUpdate, GrantStatus, UpdateCategory, Visibility
from notifications.services import notify

from .models import Appointment, AppointmentStatus, AppointmentType


def _family(case):
    return [g.user for g in BeneficiaryAccessGrant.objects.filter(case=case, status=GrantStatus.ACTIVE).select_related("user")]


def _officers(case):
    return {case.assigned_officer}


def _check(user, case, appt_type):
    if not access.is_on_team(user, case):
        raise PermissionDenied("You are not on this case team.")
    if appt_type == AppointmentType.COURT_HEARING and user.role != Role.COURT:
        raise PermissionDenied("Only court registry officers can schedule court hearings.")


@transaction.atomic
def create_appointment(user, data, request=None):
    case = data["case"]
    _check(user, case, data["type"])
    appt = Appointment.objects.create(institution=user.institution, created_by=user, **data)
    CaseUpdate.objects.create(
        case=case, institution=user.institution, author=user, category=UpdateCategory.APPOINTMENT,
        note=f"{appt.get_type_display()} scheduled for {timezone.localtime(appt.scheduled_for):%d %b %Y %H:%M}.",
        visibility=Visibility.CASE_TEAM, system_generated=True,
    )
    for u in _officers(case):
        notify(u, "APPOINTMENT_SCHEDULED", link=f"/app/cases/{case.id}", dedup_key=f"appt:{appt.id}:staff")
    if appt.visible_to_beneficiary:
        for u in _family(case):
            notify(u, "APPOINTMENT_SCHEDULED", link=f"/me/cases/{case.id}", dedup_key=f"appt:{appt.id}")
    record(user, "appointment.create", appt, request=request, case_id=str(case.id), type=appt.type)
    return appt


@transaction.atomic
def update_appointment(user, appt, data, request=None):
    if data.get("case") and data["case"].id != appt.case_id:
        raise ValidationError({"case_id": ["An appointment cannot be moved to another case."]})
    _check(user, appt.case, data.get("type", appt.type))
    if appt.institution_id != user.institution.id:
        raise PermissionDenied("Only the institution that scheduled this appointment can change it.")
    new_time = data.get("scheduled_for")
    changed_time = new_time is not None and new_time != appt.scheduled_for
    if changed_time:
        appt.previous_scheduled_for = appt.scheduled_for
        appt.reminder_sent_at = None
        data.setdefault("status", AppointmentStatus.RESCHEDULED)
    for k, v in data.items():
        if k != "case":
            setattr(appt, k, v)
    appt.save()
    case = appt.case
    if changed_time or appt.status == AppointmentStatus.CANCELLED:
        CaseUpdate.objects.create(
            case=case, institution=user.institution, author=user, category=UpdateCategory.APPOINTMENT,
            note=f"{appt.get_type_display()} {appt.get_status_display().lower()}"
                 + (f" to {timezone.localtime(appt.scheduled_for):%d %b %Y %H:%M}." if changed_time else "."),
            visibility=Visibility.CASE_TEAM, system_generated=True,
        )
        stamp = int(timezone.now().timestamp())
        if appt.visible_to_beneficiary:
            for u in _family(case):
                notify(u, "APPOINTMENT_CHANGED", link=f"/me/cases/{case.id}", dedup_key=f"appt-chg:{appt.id}:{stamp}")
        for u in _officers(case):
            notify(u, "APPOINTMENT_CHANGED", link=f"/app/cases/{case.id}", dedup_key=f"appt-chg:{appt.id}:{stamp}:staff")
    if appt.status == AppointmentStatus.MISSED:
        for u in _officers(case):
            notify(u, "APPOINTMENT_MISSED", link=f"/app/cases/{case.id}", dedup_key=f"appt-missed:{appt.id}")
    record(user, "appointment.update", appt, request=request, status=appt.status, rescheduled=changed_time)
    return appt


def send_due_reminders(hours_ahead=48, now=None):
    """Send one discreet reminder per appointment (per schedule) to the family and responsible officer."""
    now = now or timezone.now()
    due = Appointment.objects.filter(
        status__in=[AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED],
        scheduled_for__gt=now, scheduled_for__lte=now + timedelta(hours=hours_ahead), reminder_sent_at__isnull=True,
    ).select_related("case", "case__assigned_officer")
    count = 0
    for appt in due:
        key = f"remind:{appt.id}:{appt.scheduled_for.isoformat()}"
        if appt.visible_to_beneficiary:
            for u in _family(appt.case):
                notify(u, "APPOINTMENT_REMINDER", link=f"/me/cases/{appt.case_id}", dedup_key=key)
        for u in _officers(appt.case):
            notify(u, "APPOINTMENT_REMINDER", link=f"/app/cases/{appt.case_id}", dedup_key=key + ":staff")
        appt.reminder_sent_at = now
        appt.save(update_fields=["reminder_sent_at", "updated_at"])
        count += 1
    return count
