from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts import views as account_views
from analytics import views as analytics_views
from appointments.views import AppointmentViewSet
from audit.views import AuditLogViewSet
from cases import beneficiary_views as ben
from cases.views import CaseUpdateViewSet, CaseViewSet, FollowUpViewSet, GrantViewSet
from communications import views as comm
from institutions.views import InstitutionViewSet
from notifications.views import NotificationViewSet
from referrals.views import ReferralViewSet
from support_services.views import AssistanceRequestStaffViewSet, SupportServiceViewSet
from translations.views import translation_status

router = DefaultRouter()
router.register("cases", CaseViewSet, basename="case")
router.register("case-updates", CaseUpdateViewSet, basename="case-update")
router.register("follow-ups", FollowUpViewSet, basename="follow-up")
router.register("access-grants", GrantViewSet, basename="access-grant")
router.register("referrals", ReferralViewSet, basename="referral")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("institutions", InstitutionViewSet, basename="institution")
router.register("support-services", SupportServiceViewSet, basename="support-service")
router.register("assistance-requests", AssistanceRequestStaffViewSet, basename="assistance-request")
router.register("anonymous-reports", comm.AnonymousReportViewSet, basename="anonymous-report")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("admin/users", account_views.AdminUserViewSet, basename="admin-user")


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/health/", health),
    path("api/auth/login/", account_views.login),
    path("api/auth/refresh/", account_views.refresh),
    path("api/auth/logout/", account_views.logout),
    path("api/auth/me/", account_views.me),
    path("api/auth/change-password/", account_views.change_password),
    path("api/auth/password-reset/", account_views.password_reset),
    path("api/auth/password-reset/confirm/", account_views.password_reset_confirm),
    path("api/beneficiary/cases/", ben.my_cases),
    path("api/beneficiary/cases/<uuid:case_id>/", ben.my_case_detail),
    path("api/beneficiary/cases/<uuid:case_id>/updates/", ben.my_case_updates),
    path("api/beneficiary/cases/<uuid:case_id>/appointments/", ben.my_case_appointments),
    path("api/beneficiary/cases/<uuid:case_id>/services/", ben.my_case_services),
    path("api/beneficiary/assistance-requests/", ben.my_assistance_requests),
    path("api/analytics/overview/", analytics_views.overview),
    path("api/analytics/referrals/", analytics_views.referrals),
    path("api/analytics/case-progress/", analytics_views.case_progress),
    path("api/communications/ussd/callback/", comm.ussd_callback),
    path("api/communications/ussd/events/", comm.ussd_events),
    path("api/communications/ussd/simulator/", comm.ussd_simulator),
    path("api/communications/sms/delivery-callback/", comm.sms_delivery_callback),
    path("api/communications/sms/dashboard/", comm.sms_dashboard),
    path("api/translations/status/", translation_status),
    path("api/", include(router.urls)),
]
