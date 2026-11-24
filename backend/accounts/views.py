from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from audit.services import record
from core.permissions import IsPlatformAdmin

from .models import User
from .serializers import AdminUserSerializer, MeSerializer

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
GENERIC_LOGIN_ERROR = "Invalid username or password."


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"


def _set_refresh_cookie(response, refresh, user):
    hours = settings.BENEFICIARY_REFRESH_HOURS if user.is_beneficiary_user else None
    if hours:
        refresh.set_exp(lifetime=timedelta(hours=hours))
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int((hours or settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds() / 3600) * 3600),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _token_response(user, request):
    refresh = RefreshToken.for_user(user)
    data = {"access": str(refresh.access_token), "user": MeSerializer(user, context={"request": request}).data}
    response = Response(data)
    _set_refresh_cookie(response, refresh, user)
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        raise ValidationError({"detail": ["Enter your username and password."]})
    candidate = User.objects.filter(username=username).first()
    if candidate and candidate.locked_until and candidate.locked_until > timezone.now():
        record(None, "auth.login_locked", candidate, request=request, success=False, security=True)
        return Response({"error": {"code": "locked", "message": "Too many failed attempts. Try again later or contact your administrator.", "details": None}}, status=403)
    user = authenticate(request, username=username, password=password)
    if user is None:
        if candidate:
            candidate.failed_login_count += 1
            if candidate.failed_login_count >= MAX_FAILED_LOGINS:
                candidate.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
                candidate.failed_login_count = 0
            candidate.save(update_fields=["failed_login_count", "locked_until"])
        record(None, "auth.login_failed", object_type="User", object_id=candidate.pk if candidate else "", request=request, success=False, security=True)
        return Response({"error": {"code": "invalid_credentials", "message": GENERIC_LOGIN_ERROR, "details": None}}, status=401)
    if user.failed_login_count or user.locked_until:
        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_count", "locked_until"])
    record(user, "auth.login", user, request=request)
    return _token_response(user, request)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if not raw:
        return Response({"error": {"code": "no_session", "message": "Please sign in.", "details": None}}, status=401)
    try:
        old = RefreshToken(raw)
        user = User.objects.get(pk=old["user_id"], is_active=True)
        old.blacklist()
    except (TokenError, User.DoesNotExist, KeyError):
        response = Response({"error": {"code": "session_expired", "message": "Your session has ended. Please sign in again.", "details": None}}, status=401)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
        return response
    return _token_response(user, request)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if raw:
        try:
            RefreshToken(raw).blacklist()
        except TokenError:
            pass
    if request.user and request.user.is_authenticated:
        record(request.user, "auth.logout", request.user, request=request)
    response = Response(status=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
    return response


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "PATCH":
        ser = MeSerializer(request.user, data={k: v for k, v in request.data.items() if k in {"preferred_language", "full_name"}}, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        from notifications.services import get_preference

        pref = get_preference(request.user)
        pref.preferred_language = request.user.preferred_language
        pref.save(update_fields=["preferred_language"])
    return Response(MeSerializer(request.user, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    if not user.check_password(request.data.get("current_password") or ""):
        raise ValidationError({"current_password": ["Current password is incorrect."]})
    new = request.data.get("new_password") or ""
    try:
        validate_password(new, user)
    except DjangoValidationError as e:
        raise ValidationError({"new_password": list(e.messages)})
    user.set_password(new)
    user.save()
    record(user, "auth.change_password", user, request=request, security=True)
    return Response({"detail": "Password changed."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset(request):
    """Always returns the same message so the endpoint cannot be used to discover accounts.
    Beneficiary and caregiver accounts are recovered in person through their support officer."""
    email = (request.data.get("email") or "").strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first() if email else None
    if user and user.is_institutional:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        send_mail("Tuliwamu password reset", f"Use this link within 3 days to set a new password:\n{link}\n\nIf you did not ask for this, contact your administrator.", None, [user.email])
        record(user, "auth.password_reset_requested", user, request=request, security=True)
    return Response({"detail": "If an eligible staff account uses this email, a reset link has been sent. Children and caregivers: please contact your support officer."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_confirm(request):
    try:
        uid = force_str(urlsafe_base64_decode(request.data.get("uid") or ""))
        user = User.objects.get(pk=uid, is_active=True)
    except Exception:
        user = None
    if user is None or not default_token_generator.check_token(user, request.data.get("token") or ""):
        raise ValidationError({"detail": ["This reset link is invalid or has expired."]})
    new = request.data.get("new_password") or ""
    try:
        validate_password(new, user)
    except DjangoValidationError as e:
        raise ValidationError({"new_password": list(e.messages)})
    user.set_password(new)
    user.failed_login_count = 0
    user.locked_until = None
    user.save()
    record(user, "auth.password_reset_completed", user, request=request, security=True)
    return Response({"detail": "Password updated. You can now sign in."})


class AdminUserViewSet(viewsets.ModelViewSet):
    """User management. Administrators manage accounts but this grants them no case access."""

    permission_classes = [IsPlatformAdmin]
    serializer_class = AdminUserSerializer
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "full_name", "email"]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return User.objects.all().order_by("role", "username").prefetch_related("memberships__institution")

    def perform_create(self, serializer):
        user = serializer.save()
        record(self.request.user, "admin.user_create", user, request=self.request, role=user.role, security=True)

    def perform_update(self, serializer):
        user = serializer.save()
        record(self.request.user, "admin.user_update", user, request=self.request, fields=sorted(serializer.validated_data.keys()), security=True)
