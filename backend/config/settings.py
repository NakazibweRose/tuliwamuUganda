"""Django settings for the Tuliwamu backend.

All deployment-specific values come from environment variables (see .env.example).
"""
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or os.environ.get("TULIWAMU_TESTING"):
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is False")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "core",
    "accounts",
    "institutions",
    "cases",
    "referrals",
    "appointments",
    "support_services",
    "notifications",
    "analytics",
    "audit",
    "translations",
    "communications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.NoStoreApiMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get(
            "DATABASE_URL", "postgres://tuliwamu:tuliwamu_dev@localhost:5432/tuliwamu"
        ),
        conn_max_age=60,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache (rate limits, lockouts, idempotency). Redis in production, memory locally. ---
if os.environ.get("REDIS_URL"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": os.environ["REDIS_URL"]}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- REST framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "login": "10/min",
        "password_reset": "5/hour",
        "ussd": "120/min",
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("ACCESS_TOKEN_MINUTES", "10"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=int(os.environ.get("REFRESH_TOKEN_HOURS", "8"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}
REFRESH_COOKIE_NAME = "tlw_refresh"
REFRESH_COOKIE_PATH = "/api/auth/"
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", not DEBUG)
# Beneficiary sessions are deliberately shorter (shared devices are common).
BENEFICIARY_REFRESH_HOURS = 2

# --- CORS / CSRF ---
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

# --- Security headers ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "no-referrer"
SESSION_COOKIE_HTTPONLY = True
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# --- Encryption at rest for the most sensitive free-text fields ---
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")

# --- Email ---
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@tuliwamu.example")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# --- Africa's Talking ---
AFRICASTALKING_USERNAME = os.environ.get("AFRICASTALKING_USERNAME", "sandbox")
AFRICASTALKING_API_KEY = os.environ.get("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_ENVIRONMENT = os.environ.get("AFRICASTALKING_ENVIRONMENT", "sandbox")
AFRICASTALKING_USSD_SERVICE_CODE = os.environ.get("AFRICASTALKING_USSD_SERVICE_CODE", "*384*1234#")
AFRICASTALKING_SMS_SENDER_ID = os.environ.get("AFRICASTALKING_SMS_SENDER_ID", "")
AFRICASTALKING_CALLBACK_TOKEN = os.environ.get("AFRICASTALKING_CALLBACK_TOKEN", "")
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "africastalking" if AFRICASTALKING_API_KEY else "mock")
SMS_TIMEOUT_SECONDS = int(os.environ.get("SMS_TIMEOUT_SECONDS", "10"))
SMS_MAX_ATTEMPTS = 3

USSD_SESSION_TTL_SECONDS = 300
USSD_MAX_REPORTS_PER_PHONE_PER_DAY = int(os.environ.get("USSD_MAX_REPORTS_PER_PHONE_PER_DAY", "3"))
EMERGENCY_CONTACT_TEXT = os.environ.get(
    "EMERGENCY_CONTACT_TEXT", "Child Helpline 116 (toll-free). Police 999 or 112."
)

# --- Analytics privacy ---
ANALYTICS_MIN_CELL_SIZE = int(os.environ.get("ANALYTICS_MIN_CELL_SIZE", "5"))

# --- Logging: never log request bodies; app loggers log identifiers only ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}
