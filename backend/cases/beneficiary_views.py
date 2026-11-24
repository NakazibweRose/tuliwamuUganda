"""Beneficiary / caregiver portal API.

Everything here is filtered through ACTIVE BeneficiaryAccessGrants and returns only content that
an officer has approved for the family. No investigation, medical, forensic or witness data is
reachable from these endpoints."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from appointments.models import Appointment, AppointmentStatus
from audit.services import record
from core.permissions import IsBeneficiaryUser
from referrals.models import Referral, ReferralStatus
from support_services.models import AssistanceRequest
from support_services.serializers import (
    AssistanceRequestBeneficiarySerializer,
    AssistanceRequestCreateSerializer,
    SupportServiceSerializer,
)
from support_services.models import SupportService
from support_services.views import create_assistance_request

from . import access
from .models import BeneficiaryStatus, CaseUpdate, JourneyStep

JOURNEY = [s.value for s in JourneyStep]


def _journey_step(case):
    latest = (
        CaseUpdate.objects.filter(case=case, beneficiary_status=BeneficiaryStatus.APPROVED)
        .exclude(beneficiary_journey_step="").order_by("-created_at").first()
    )
    return latest.beneficiary_journey_step if latest else JourneyStep.REPORTED


def _appointments(case):
    return Appointment.objects.filter(case=case, visible_to_beneficiary=True).exclude(status=AppointmentStatus.CANCELLED)


def _appointment_dict(a):
    return {
        "id": str(a.id), "type": a.type, "scheduled_for": a.scheduled_for, "previous_scheduled_for": a.previous_scheduled_for,
        "status": a.status, "public_location": a.public_location, "note": a.beneficiary_note,
        "institution": a.institution.name,
    }


def _case_summary(case, grant):
    upcoming = _appointments(case).filter(scheduled_for__gte=timezone.now()).order_by("scheduled_for").first()
    last = CaseUpdate.objects.filter(case=case, beneficiary_status=BeneficiaryStatus.APPROVED).order_by("-created_at").first()
    officer = case.assigned_officer
    return {
        "id": str(case.id),
        "reference": case.reference,
        "relationship": grant.relationship,
        "journey_step": _journey_step(case),
        "journey": JOURNEY,
        "last_update_at": last.created_at if last else None,
        "last_update_message": last.beneficiary_message if last else None,
        "next_appointment": _appointment_dict(upcoming) if upcoming else None,
        "support_officer": {
            "name": officer.display_name(),
            "institution": case.lead_institution.name,
            "contact": case.lead_institution.public_contact,
        },
    }


def _grant_for(user, case_id):
    return get_object_or_404(access.active_grants(user).select_related("case", "case__lead_institution", "case__assigned_officer"), case_id=case_id)


@api_view(["GET"])
@permission_classes([IsBeneficiaryUser])
def my_cases(request):
    grants = access.active_grants(request.user).select_related("case", "case__lead_institution", "case__assigned_officer")
    return Response([_case_summary(g.case, g) for g in grants])


@api_view(["GET"])
@permission_classes([IsBeneficiaryUser])
def my_case_detail(request, case_id):
    grant = _grant_for(request.user, case_id)
    record(request.user, "beneficiary.view_case", grant.case, request=request)
    return Response(_case_summary(grant.case, grant))


@api_view(["GET"])
@permission_classes([IsBeneficiaryUser])
def my_case_updates(request, case_id):
    grant = _grant_for(request.user, case_id)
    updates = CaseUpdate.objects.filter(case=grant.case, beneficiary_status=BeneficiaryStatus.APPROVED).select_related("institution")
    return Response([
        {"id": str(u.id), "date": u.reviewed_at or u.created_at, "message": u.beneficiary_message,
         "journey_step": u.beneficiary_journey_step or None, "institution_type": u.institution.type}
        for u in updates.order_by("created_at")
    ])


@api_view(["GET"])
@permission_classes([IsBeneficiaryUser])
def my_case_appointments(request, case_id):
    grant = _grant_for(request.user, case_id)
    return Response([_appointment_dict(a) for a in _appointments(grant.case).select_related("institution")])


@api_view(["GET"])
@permission_classes([IsBeneficiaryUser])
def my_case_services(request, case_id):
    grant = _grant_for(request.user, case_id)
    referrals = Referral.objects.filter(case=grant.case, visible_to_beneficiary=True).exclude(
        status__in=[ReferralStatus.DRAFT, ReferralStatus.CANCELLED, ReferralStatus.DECLINED]
    ).select_related("receiving_institution")
    connected = [
        {"category": r.category, "status": "COMPLETED" if r.status == ReferralStatus.COMPLETED else "ARRANGED",
         "institution": r.receiving_institution.name, "contact": r.receiving_institution.public_contact}
        for r in referrals
    ]
    directory = SupportServiceSerializer(SupportService.objects.filter(is_active=True).select_related("institution"), many=True).data
    return Response({"connected": connected, "directory": directory})


class AssistanceThrottle(UserRateThrottle):
    scope = "assistance"
    rate = "10/hour"

    def allow_request(self, request, view):
        return True if request.method == "GET" else super().allow_request(request, view)


@api_view(["GET", "POST"])
@permission_classes([IsBeneficiaryUser])
@throttle_classes([AssistanceThrottle])
def my_assistance_requests(request):
    if request.method == "GET":
        qs = AssistanceRequest.objects.filter(requested_by=request.user, case__in=access.beneficiary_cases(request.user)).select_related("case")
        return Response(AssistanceRequestBeneficiarySerializer(qs, many=True).data)
    ser = AssistanceRequestCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    grant = _grant_for(request.user, ser.validated_data["case_id"])
    req = create_assistance_request(request.user, grant.case, ser.validated_data, request=request)
    return Response(AssistanceRequestBeneficiarySerializer(req).data, status=status.HTTP_201_CREATED)
