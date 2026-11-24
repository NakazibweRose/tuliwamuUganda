"""USSD menu engine shared by the Africa's Talking callback and the web simulator.

Africa's Talking sends the *whole* input history in `text`, joined by "*", on every request.
We keep per-session state in UssdSession and work out the newest input by comparing `text` with
the text we processed last. This:
* returns the stored response when the same callback arrives twice (idempotent), and
* lets free-text answers contain "*" without breaking the menu.

Privacy: the phone number is only used, salted and hashed, as a short-lived rate-limit key in the
cache. It is never written to the database unless the reporter types it as a safe contact.
"""
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.references import unique_reference
from translations.catalog import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, t

from ..models import AnonymousCategory, AnonymousReport, ReviewStatus, UssdSession
from ..sms.services import normalise_ug_phone

CATEGORY_BY_OPTION = {
    "1": AnonymousCategory.SEXUAL_ABUSE, "2": AnonymousCategory.PHYSICAL_VIOLENCE, "3": AnonymousCategory.NEGLECT,
    "4": AnonymousCategory.EXPLOITATION, "5": AnonymousCategory.TRAFFICKING, "6": AnonymousCategory.OTHER,
}
DANGER_BY_OPTION = {"1": "YES", "2": "NO", "3": "UNSURE"}
MAX_INVALID = 3
MAX_PIN_FAILURES = 5


@dataclass
class UssdResult:
    text: str
    end: bool

    def render(self):
        return ("END " if self.end else "CON ") + self.text


def _phone_key(phone, purpose):
    day = timezone.localdate().isoformat()
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{purpose}:{day}:{phone}".encode()).hexdigest()[:40]
    return f"ussd:{purpose}:{digest}"


def _language_menu():
    lines = [f"{i + 1}. {LANGUAGE_NAMES[code]}" for i, code in enumerate(SUPPORTED_LANGUAGES)]
    return t("ussd.welcome", "en") + "\n" + "\n".join(lines)


class UssdEngine:
    def __init__(self, channel="USSD"):
        self.channel = channel

    # ---- public entry point ----
    def handle(self, session_id, phone_number, service_code, text):
        text = (text or "").strip()
        now = timezone.now()
        with transaction.atomic():
            session = UssdSession.objects.select_for_update().filter(session_id=session_id).first()
            if session and session.expires_at < now:
                session.delete()
                session = None
            if session is None:
                session = UssdSession.objects.create(
                    session_id=session_id, current_menu="LANG",
                    expires_at=now + timedelta(seconds=settings.USSD_SESSION_TTL_SECONDS),
                )
                if text == "":
                    result = UssdResult(_language_menu(), False)
                    return self._save(session, text, result)
                # A session we never saw that already carries input: replay from scratch.
                result = UssdResult(_language_menu(), False)
                for part in text.split("*"):
                    result = self._step(session, part, phone_number)
                    if result.end:
                        break
                return self._save(session, text, result)

            if text == session.last_text:  # duplicate callback
                return UssdResult(session.last_response[4:], session.last_response.startswith("END"))

            if session.last_text and text.startswith(session.last_text + "*"):
                new_input = text[len(session.last_text) + 1:]
            elif not session.last_text:
                new_input = text
            else:  # out-of-sync input; take the last segment
                new_input = text.split("*")[-1]
            result = self._step(session, new_input, phone_number)
            return self._save(session, text, result)

    # ---- internals ----
    def _save(self, session, text, result):
        session.last_text = text
        session.last_response = result.render()
        if result.end:
            # Drop temporary answers as soon as the conversation is over.
            session.temporary_session_data = {}
        session.save()
        return result

    @property
    def lang(self):
        return self._lang

    def _step(self, session, value, phone):
        value = (value or "").strip()
        self._lang = session.selected_language or "en"
        menu = session.current_menu
        handler = getattr(self, f"_menu_{menu.lower()}")
        return handler(session, value, phone)

    def _invalid(self, session, prompt_key, **kw):
        session.invalid_attempts += 1
        if session.invalid_attempts >= MAX_INVALID:
            return UssdResult(t("ussd.too_many_invalid", self.lang), True)
        prompt = _language_menu() if prompt_key == "LANG" else t(prompt_key, self.lang, **kw)
        return UssdResult(t("ussd.invalid", self.lang) + "\n" + prompt, False)

    def _go(self, session, menu, prompt_key, **kw):
        session.current_menu = menu
        session.invalid_attempts = 0
        return UssdResult(t(prompt_key, self.lang, **kw), False)

    def _data(self, session):
        return session.temporary_session_data

    def _menu_lang(self, session, value, phone):
        if value in {str(i + 1) for i in range(len(SUPPORTED_LANGUAGES))}:
            session.selected_language = SUPPORTED_LANGUAGES[int(value) - 1]
            self._lang = session.selected_language
            return self._go(session, "MAIN", "ussd.main")
        return self._invalid(session, "LANG")

    def _menu_main(self, session, value, phone):
        if value == "1":
            return self._go(session, "R_DANGER", "ussd.danger")
        if value == "2":
            return self._go(session, "C_REF", "ussd.check_ref")
        if value == "3":
            return UssdResult(t("ussd.services", self.lang, emergency=settings.EMERGENCY_CONTACT_TEXT), True)
        if value == "4":
            return UssdResult(t("ussd.exit", self.lang), True)
        return self._invalid(session, "ussd.main")

    # Reporting flow
    def _menu_r_danger(self, session, value, phone):
        if value not in DANGER_BY_OPTION:
            return self._invalid(session, "ussd.danger")
        self._data(session)["danger"] = DANGER_BY_OPTION[value]
        result = self._go(session, "R_CATEGORY", "ussd.category")
        if value == "1":
            result.text = t("ussd.danger_advice", self.lang, emergency=settings.EMERGENCY_CONTACT_TEXT) + "\n" + result.text
        return result

    def _menu_r_category(self, session, value, phone):
        if value not in CATEGORY_BY_OPTION:
            return self._invalid(session, "ussd.category")
        self._data(session)["category"] = CATEGORY_BY_OPTION[value]
        return self._go(session, "R_LOCATION", "ussd.location")

    def _menu_r_location(self, session, value, phone):
        if not (2 <= len(value) <= 40) or not any(c.isalpha() for c in value):
            return self._invalid(session, "ussd.location_invalid")
        self._data(session)["location"] = value
        return self._go(session, "R_DESC", "ussd.description")

    def _menu_r_desc(self, session, value, phone):
        if not (5 <= len(value) <= 160):
            return self._invalid(session, "ussd.description_invalid")
        self._data(session)["description"] = value
        return self._go(session, "R_CONTACT", "ussd.contact_choice")

    def _menu_r_contact(self, session, value, phone):
        if value == "1":
            return self._go(session, "R_PRIVACY", "ussd.privacy")
        if value == "2":
            return self._go(session, "R_CONTACT_NUMBER", "ussd.contact_number")
        return self._invalid(session, "ussd.contact_choice")

    def _menu_r_contact_number(self, session, value, phone):
        if value == "0":
            return self._go(session, "R_PRIVACY", "ussd.privacy")
        normalised = normalise_ug_phone(value)
        if not normalised:
            return self._invalid(session, "ussd.contact_invalid")
        self._data(session)["safe_contact"] = normalised
        return self._go(session, "R_PRIVACY", "ussd.privacy")

    def _menu_r_privacy(self, session, value, phone):
        if value == "1":
            return self._go(session, "R_CONFIRM", "ussd.confirm")
        if value == "2":
            return UssdResult(t("ussd.cancelled", self.lang), True)
        return self._invalid(session, "ussd.privacy")

    def _menu_r_confirm(self, session, value, phone):
        if value == "2":
            return UssdResult(t("ussd.cancelled", self.lang), True)
        if value != "1":
            return self._invalid(session, "ussd.confirm")
        if session.report_id:  # already submitted in this session (repeated callback)
            return UssdResult(t("ussd.submitted", self.lang, reference=session.report.reference_code, pin="****",
                                emergency=settings.EMERGENCY_CONTACT_TEXT), True)
        key = _phone_key(phone or session.session_id, "reports")
        if cache.get(key, 0) >= settings.USSD_MAX_REPORTS_PER_PHONE_PER_DAY:
            return UssdResult(t("ussd.rate_limited", self.lang, emergency=settings.EMERGENCY_CONTACT_TEXT), True)
        report, pin = self._create_report(session)
        cache.set(key, cache.get(key, 0) + 1, timeout=60 * 60 * 24)
        session.report = report
        return UssdResult(t("ussd.submitted", self.lang, reference=report.reference_code, pin=pin,
                            emergency=settings.EMERGENCY_CONTACT_TEXT), True)

    def _create_report(self, session):
        d = self._data(session)
        pin = f"{secrets.randbelow(10000):04d}"
        report = AnonymousReport.objects.create(
            reference_code=unique_reference(AnonymousReport, "reference_code", "AR", length=6),
            pin_hash=make_password(pin),
            channel=self.channel,
            category=d["category"],
            immediate_danger=d["danger"],
            general_location=d["location"],
            description=d["description"],
            preferred_language=session.selected_language or "en",
            optional_safe_contact=d.get("safe_contact", ""),
            review_status=ReviewStatus.URGENT if d["danger"] == "YES" else ReviewStatus.NEW,
        )
        from .notify import alert_triage_officers

        alert_triage_officers(report)
        return report, pin

    # Status check flow
    def _menu_c_ref(self, session, value, phone):
        ref = value.upper().replace(" ", "")
        if not ref.startswith("AR-") and len(ref) == 6:
            ref = "AR-" + ref
        self._data(session)["ref"] = ref
        return self._go(session, "C_PIN", "ussd.check_pin")

    def _menu_c_pin(self, session, value, phone):
        emergency = settings.EMERGENCY_CONTACT_TEXT
        lock_key = _phone_key(phone or session.session_id, "pinfail")
        if cache.get(lock_key, 0) >= MAX_PIN_FAILURES:
            return UssdResult(t("ussd.check_locked", self.lang, emergency=emergency), True)
        report = AnonymousReport.objects.filter(reference_code=self._data(session).get("ref", "")).first()
        if report is None or report.failed_status_checks >= MAX_PIN_FAILURES or not check_password(value, report.pin_hash):
            cache.set(lock_key, cache.get(lock_key, 0) + 1, timeout=60 * 60 * 24)
            if report is not None:
                report.failed_status_checks += 1
                report.save(update_fields=["failed_status_checks"])
                if report.failed_status_checks >= MAX_PIN_FAILURES:
                    return UssdResult(t("ussd.check_locked", self.lang, emergency=emergency), True)
            return UssdResult(t("ussd.check_failed", self.lang, emergency=emergency), True)
        status_text = t(f"ussd.status.{report.review_status}", self.lang)
        return UssdResult(t("ussd.status", self.lang, reference=report.reference_code, status=status_text), True)


def purge_expired_sessions(now=None):
    return UssdSession.objects.filter(expires_at__lt=now or timezone.now()).delete()[0]
