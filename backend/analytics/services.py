"""Anonymised aggregate indicators.

Privacy rules:
* Only counts/rates; never row-level data or case references.
* Geography at region level; district counts only appear when they meet the threshold.
* Time at month level only.
* Any count between 1 and K-1 (K = ANALYTICS_MIN_CELL_SIZE) is suppressed and returned as null
  with suppressed=true. Rates whose denominator is below K are also suppressed.
* No cross-tabulation of age × location × category.
"""
from django.conf import settings
from django.db.models import Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncMonth
from django.utils import timezone

from appointments.models import Appointment
from cases.models import CaseStage, ChildCase, FollowUp, IncidentCategory
from institutions.models import Region
from referrals.models import Referral, ReferralCategory, ReferralStatus
from support_services.models import AssistanceRequest


def k():
    return settings.ANALYTICS_MIN_CELL_SIZE


def cell(n):
    if 0 < n < k():
        return {"value": None, "suppressed": True}
    return {"value": n, "suppressed": False}


def rate(numer, denom):
    if denom < k():
        return {"value": None, "suppressed": True}
    return {"value": round(100 * numer / denom, 1), "suppressed": False}


def grouped(qs, field, choices):
    counts = dict(qs.values_list(field).annotate(n=Count("id")).values_list(field, "n"))
    return [{"key": key, "label": label, **cell(counts.get(key, 0))} for key, label in choices]


def overview():
    cases = ChildCase.objects.all()
    refs = Referral.objects.exclude(status=ReferralStatus.DRAFT)
    total_cases = cases.count()
    total_refs = refs.count()
    completed = refs.filter(status=ReferralStatus.COMPLETED).count()
    acknowledged = refs.filter(acknowledged_at__isnull=False).count()
    pending = refs.filter(status__in=[ReferralStatus.SENT, ReferralStatus.RETURNED]).count()
    in_progress = refs.filter(status__in=[ReferralStatus.ACKNOWLEDGED, ReferralStatus.IN_PROGRESS]).count()

    ack_delta = refs.filter(acknowledged_at__isnull=False, sent_at__isnull=False).annotate(
        d=ExpressionWrapper(F("acknowledged_at") - F("sent_at"), output_field=DurationField())
    ).values_list("d", flat=True)
    ack_list = list(ack_delta)
    avg_ack_hours = None
    if len(ack_list) >= k():
        avg_ack_hours = round(sum(d.total_seconds() for d in ack_list) / len(ack_list) / 3600, 1)

    fus = FollowUp.objects.exclude(status="CANCELLED")
    fu_done = fus.filter(status="DONE").count()
    assist = AssistanceRequest.objects.all()
    assist_resp = assist.filter(responded_at__isnull=False).count()
    hearings = Appointment.objects.filter(type="COURT_HEARING")
    appts = Appointment.objects.filter(scheduled_for__lt=timezone.now()).exclude(status="CANCELLED")

    return {
        "min_cell_size": k(),
        "generated_at": timezone.now(),
        "totals": {
            "cases": cell(total_cases),
            "open_cases": cell(cases.filter(closed_at__isnull=True).count()),
            "referrals": cell(total_refs),
            "referrals_completed": cell(completed),
            "referrals_pending_acknowledgement": cell(pending),
            "referrals_in_progress": cell(in_progress),
            "institutions_active": cell(Referral.objects.values("receiving_institution").distinct().count()),
            "court_hearings_scheduled": cell(hearings.count()),
        },
        "rates": {
            "referral_acknowledgement_rate": rate(acknowledged, total_refs),
            "referral_completion_rate": rate(completed, total_refs),
            "follow_up_completion_rate": rate(fu_done, fus.count()),
            "assistance_response_rate": rate(assist_resp, assist.count()),
            "appointments_with_reminder_rate": rate(appts.filter(reminder_sent_at__isnull=False).count(), appts.count()),
        },
        "avg_acknowledgement_hours": {"value": avg_ack_hours, "suppressed": avg_ack_hours is None and len(ack_list) > 0},
        "cases_by_category": grouped(cases, "incident_category", IncidentCategory.choices),
        "cases_by_region": grouped(cases, "region", Region.choices),
    }


def referral_analytics():
    refs = Referral.objects.exclude(status=ReferralStatus.DRAFT)
    by_category = []
    for key, label in ReferralCategory.choices:
        sub = refs.filter(category=key)
        total = sub.count()
        done = sub.filter(status=ReferralStatus.COMPLETED).count()
        waiting = sub.filter(status__in=[ReferralStatus.SENT, ReferralStatus.RETURNED]).count()
        declined = sub.filter(status=ReferralStatus.DECLINED).count()
        by_category.append({
            "key": key, "label": label, "total": cell(total), "completed": cell(done), "awaiting_acknowledgement": cell(waiting),
            "declined": cell(declined), "completion_rate": rate(done, total),
        })
    by_status = grouped(refs, "status", [c for c in ReferralStatus.choices if c[0] != "DRAFT"])
    stale_cutoff = timezone.now() - timezone.timedelta(days=7)
    stale = refs.filter(status=ReferralStatus.SENT, sent_at__lt=stale_cutoff)
    gaps = []
    for row in by_category:
        reasons = []
        if row["awaiting_acknowledgement"]["value"] and row["total"]["value"] and row["awaiting_acknowledgement"]["value"] / row["total"]["value"] >= 0.3:
            reasons.append("AWAITING_ACK")
        if row["completion_rate"]["value"] is not None and row["completion_rate"]["value"] < 40:
            reasons.append("LOW_COMPLETION")
        if row["declined"]["value"]:
            reasons.append("DECLINED")
        if reasons:
            gaps.append({"category": row["key"], "label": row["label"], "reasons": reasons})
    monthly = list(
        refs.filter(sent_at__isnull=False).annotate(month=TruncMonth("sent_at")).values("month").annotate(n=Count("id")).order_by("month")
    )
    return {
        "min_cell_size": k(),
        "by_category": by_category,
        "by_status": by_status,
        "unacknowledged_over_7_days": cell(stale.count()),
        "service_gaps": gaps,
        "monthly": [{"month": m["month"].strftime("%Y-%m"), **cell(m["n"])} for m in monthly],
    }


def case_progress():
    cases = ChildCase.objects.all()
    stages = [(s.code, s.label) for s in CaseStage.objects.filter(is_active=True)]
    monthly = list(cases.annotate(month=TruncMonth("date_reported")).values("month").annotate(n=Count("id")).order_by("month"))
    return {
        "min_cell_size": k(),
        "by_stage": grouped(cases, "stage_id", stages),
        "court": {
            "cases_in_court_stages": cell(cases.filter(stage__journey_step="COURT").count()),
            "cases_concluded": cell(cases.filter(stage__journey_step="CONCLUDED").count()),
            "hearings_rescheduled": cell(Appointment.objects.filter(type="COURT_HEARING", previous_scheduled_for__isnull=False).count()),
        },
        "monthly_registrations": [{"month": m["month"].strftime("%Y-%m"), **cell(m["n"])} for m in monthly],
    }
