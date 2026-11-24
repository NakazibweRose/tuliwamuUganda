from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from audit.services import record
from core.permissions import CanViewAnalytics

from . import services


@api_view(["GET"])
@permission_classes([CanViewAnalytics])
def overview(request):
    record(request.user, "analytics.view", object_type="Analytics", object_id="overview", request=request)
    return Response(services.overview())


@api_view(["GET"])
@permission_classes([CanViewAnalytics])
def referrals(request):
    return Response(services.referral_analytics())


@api_view(["GET"])
@permission_classes([CanViewAnalytics])
def case_progress(request):
    return Response(services.case_progress())
