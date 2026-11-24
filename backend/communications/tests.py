import uuid
from datetime import datetime, timedelta
from unittest import mock

from django.db import connection
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from communications.models import AnonymousReport, SmsMessage, UssdSession
from communications.sms import services as sms_services
from communications.sms.providers import ProviderResult
from communications.ussd.engine import UssdEngine, purge_expired_sessions
from core.testing import World
from notifications.models import NotificationPreference
from notifications.services import notify

PHONE = "+256700000099"


class UssdFlowTests(World):
    def dial(self, session, text, phone=PHONE):
        return APIClient().post("/api/communications/ussd/callback/",
                                {"sessionId": session, "serviceCode": "*384*1#", "phoneNumber": phone, "text": text})

    def run_report(self, session="s1", lang="1", contact=None, phone=PHONE):
        steps = [lang, "1", "1", "2", "Wakiso", "Child seen crying * afraid at home"]
        steps += ["2", contact] if contact else ["1"]
        steps += ["1", "1"]
        text, r = "", self.dial(session, "", phone)
        for s in steps:
            text = s if not text else f"{text}*{s}"
            r = self.dial(session, text, phone)
        return r

    def test_first_screen_is_language_menu(self):
        r = self.dial("s0", "")
        body = r.content.decode()
        self.assertTrue(body.startswith("CON WELCOME TO TULIWAMU"))
        for lang in ("English", "Kiswahili", "Luganda", "Runyankole", "Acholi", "Ateso"):
            self.assertIn(lang, body)
        self.assertEqual(r["Content-Type"], "text/plain")

    def test_all_six_languages_selectable(self):
        for i in range(1, 7):
            r = self.dial(f"lang{i}", str(i))
            self.assertTrue(r.content.decode().startswith("CON "), i)
            self.assertEqual(UssdSession.objects.get(session_id=f"lang{i}").current_menu, "MAIN")

    def test_anonymous_report_submission(self):
        r = self.run_report()
        body = r.content.decode()
        self.assertTrue(body.startswith("END Report received. Ref: AR-"), body)
        report = AnonymousReport.objects.get()
        self.assertIn(report.reference_code, body)
        self.assertEqual(report.verification_status, "UNVERIFIED")
        self.assertEqual(report.review_status, "URGENT")  # immediate danger = yes
        self.assertEqual(report.category, "PHYSICAL_VIOLENCE")
        self.assertIn("*", report.description)  # free text with '*' survives
        self.assertEqual(report.optional_safe_contact, "")
        self.assertIsNone(report.converted_case)

    def test_phone_number_is_not_persisted(self):
        self.run_report()
        tables = ["communications_anonymousreport", "communications_ussdsession", "audit_auditlog"]
        with connection.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT * FROM {table}")
                self.assertNotIn("700000099", str(cur.fetchall()), table)

    def test_optional_safe_contact_only_when_given(self):
        self.run_report(contact="0772000111")
        self.assertEqual(AnonymousReport.objects.get().optional_safe_contact, "+256772000111")

    def test_swahili_flow(self):
        r = self.dial("sw1", "2")
        self.assertIn("Chagua", r.content.decode())

    def test_invalid_input_reprompts_then_ends(self):
        self.dial("inv", "")
        r = self.dial("inv", "9")
        self.assertTrue(r.content.decode().startswith("CON Invalid choice"))
        self.dial("inv", "9*9")
        r = self.dial("inv", "9*9*9")
        self.assertTrue(r.content.decode().startswith("END"))

    def test_duplicate_callbacks_are_idempotent(self):
        self.run_report(session="dup")
        last_text = UssdSession.objects.get(session_id="dup").last_text
        again = self.dial("dup", last_text)
        self.assertTrue(again.content.decode().startswith("END Report received"))
        self.assertEqual(AnonymousReport.objects.count(), 1)

    def test_session_expiry_restarts_and_purges(self):
        self.dial("exp", "")
        UssdSession.objects.filter(session_id="exp").update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(purge_expired_sessions(), 1)
        self.assertTrue(self.dial("exp", "").content.decode().startswith("CON WELCOME"))

    def test_temporary_answers_deleted_after_submission(self):
        self.run_report(session="tmp")
        self.assertEqual(UssdSession.objects.get(session_id="tmp").temporary_session_data, {})

    @override_settings(USSD_MAX_REPORTS_PER_PHONE_PER_DAY=2)
    def test_rate_limit_per_line(self):
        for i in range(2):
            self.run_report(session=f"rl{i}")
        r = self.run_report(session="rl3")
        self.assertIn("cannot accept more reports", r.content.decode())
        self.assertEqual(AnonymousReport.objects.count(), 2)

    def test_status_check_with_reference_and_pin(self):
        body = self.run_report().content.decode()
        ref = body.split("Ref: ")[1].split(" ")[0]
        pin = body.split("PIN: ")[1].split(".")[0]
        r = self.dial("chk", f"1*2*{ref}*{pin}", phone="+256700000098")
        self.assertIn("being assessed as a priority", r.content.decode())
        bad = self.dial("chk2", f"1*2*{ref}*0000" if pin != "0000" else f"1*2*{ref}*1111", phone="+256700000097")
        self.assertIn("not recognised", bad.content.decode())
        self.assertNotIn("PHYSICAL", r.content.decode())

    @override_settings(AFRICASTALKING_CALLBACK_TOKEN="s3cret")
    def test_callback_token_enforced_when_configured(self):
        self.assertEqual(self.dial("tok", "").status_code, 403)
        ok = APIClient().post("/api/communications/ussd/callback/?token=s3cret", {"sessionId": "tok", "text": ""})
        self.assertEqual(ok.status_code, 200)

    def test_simulator_uses_same_engine(self):
        self.assertEqual(self.client_for(self.police).post("/api/communications/ussd/simulator/", {"sessionId": str(uuid.uuid4()), "text": ""}, format="json").status_code, 403)
        self.assertEqual(self.client_for(self.caregiver).post("/api/communications/ussd/simulator/", {"sessionId": str(uuid.uuid4()), "text": ""}, format="json").status_code, 403)
        c = self.client_for(self.user("complainant", "COMPLAINANT"))
        sid = str(uuid.uuid4())
        first = c.post("/api/communications/ussd/simulator/", {"sessionId": sid, "text": ""}, format="json")
        self.assertTrue(first.data["response"].startswith("CON WELCOME TO TULIWAMU"))
        text = ""
        for s in ["1", "1", "2", "3", "Gulu", "Children left alone", "1", "1", "1"]:
            text = s if not text else f"{text}*{s}"
            r = c.post("/api/communications/ussd/simulator/", {"sessionId": sid, "text": text}, format="json")
        self.assertTrue(r.data["end"])
        self.assertEqual(AnonymousReport.objects.get().channel, "SIMULATOR")
        self.assertEqual(APIClient().post("/api/communications/ussd/simulator/", {"sessionId": sid, "text": ""}).status_code, 401)


class AnonymousReportTriageTests(World):
    def setUp(self):
        super().setUp()
        UssdEngine("SIMULATOR")  # import check
        r = APIClient()
        text = ""
        for s in ["", "1", "1", "2", "1", "Kampala", "Concern about a child", "1", "1", "1"]:
            text = s if not text else (f"{text}*{s}" if s else text)
            r.post("/api/communications/ussd/callback/", {"sessionId": "tri", "phoneNumber": PHONE, "text": text})
        self.report = AnonymousReport.objects.get()

    def test_only_triage_roles_can_view(self):
        self.assertEqual(self.client_for(self.police).get("/api/anonymous-reports/").status_code, 200)
        self.assertEqual(self.client_for(self.police2).get(f"/api/anonymous-reports/{self.report.id}/").status_code, 200)
        for u in (self.probation_officer, self.medic, self.prosecutor, self.clerk, self.admin, self.caregiver):
            self.assertEqual(self.client_for(u).get("/api/anonymous-reports/").status_code, 403)

    def test_report_is_not_auto_converted_and_conversion_needs_assessment(self):
        c = self.client_for(self.police)
        url = f"/api/anonymous-reports/{self.report.id}/"
        self.assertEqual(c.post(url + "convert-to-case/", {"district": "Kampala", "region": "CENTRAL"}, format="json").status_code, 400)
        c.post(url + "review/", {"review_status": "UNDER_REVIEW", "verification_status": "CREDIBLE", "note": "Called safe contact"}, format="json")
        r = c.post(url + "convert-to-case/", {"district": "Kampala", "region": "CENTRAL"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["review_status"], "CONVERTED")
        self.assertIsNotNone(r.data["converted_case_reference"])
        self.assertGreaterEqual(len(r.data["events"]), 2)

    def test_closing_requires_reason(self):
        c = self.client_for(self.police)
        url = f"/api/anonymous-reports/{self.report.id}/review/"
        self.assertEqual(c.post(url, {"review_status": "CLOSED"}, format="json").status_code, 400)
        self.assertEqual(c.post(url, {"review_status": "CLOSED", "verification_status": "MALICIOUS", "note": "Spam"}, format="json").status_code, 200)


class SmsTests(World):
    def prefs(self, user, **kw):
        defaults = dict(preferred_channel="SMS", sms_consent=True, safe_phone="0772000123", consent_reference="TEST-CONSENT",
                        quiet_hours_start=22, quiet_hours_end=6)
        defaults.update(kw)
        NotificationPreference.objects.update_or_create(user=user, defaults=defaults)

    def noon(self):
        return timezone.make_aware(datetime(2026, 11, 20, 12, 0))

    def test_mock_provider_marks_simulated_never_delivered(self):
        self.prefs(self.caregiver)
        sms = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "k1", now=self.noon())
        self.assertEqual(sms.delivery_status, "SIMULATED")
        self.assertIsNone(sms.delivered_at)
        self.assertEqual(sms.phone_masked[:5], "+2567")
        self.assertNotIn("772000123", sms.phone_masked)

    def test_blocked_without_consent(self):
        self.prefs(self.caregiver, sms_consent=False)
        self.assertEqual(sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "k2", now=self.noon()).delivery_status, "BLOCKED")

    def test_deferred_during_quiet_hours_then_sent(self):
        self.prefs(self.caregiver)
        night = timezone.make_aware(datetime(2026, 11, 20, 23, 0))
        sms = sms_services.send_discreet_sms(self.caregiver, "APPOINTMENT_REMINDER", "k3", now=night)
        self.assertEqual(sms.delivery_status, "DEFERRED")
        self.assertEqual(timezone.localtime(sms.send_after).hour, 6)
        sms_services.process_queue(now=sms.send_after + timedelta(minutes=1))
        sms.refresh_from_db()
        self.assertEqual(sms.delivery_status, "SIMULATED")

    def test_duplicates_prevented(self):
        self.prefs(self.caregiver)
        a = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "same", now=self.noon())
        b = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "same", now=self.noon())
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(SmsMessage.objects.count(), 1)

    def test_sms_text_is_discreet(self):
        self.prefs(self.caregiver)
        sms = sms_services.send_discreet_sms(self.caregiver, "APPOINTMENT_SCHEDULED", "k4", now=self.noon())
        for word in ("court", "abuse", "victim", "child", self.case.reference):
            self.assertNotIn(word.lower(), sms.body.lower())

    def test_language_preference_used(self):
        self.prefs(self.caregiver, preferred_language="sw")
        sms = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "k5", now=self.noon())
        self.assertIn("Tafadhali", sms.body)

    @override_settings(SMS_PROVIDER="africastalking", AFRICASTALKING_API_KEY="test-key")
    def test_africastalking_failure_recorded_and_retried(self):
        self.prefs(self.caregiver)
        with mock.patch("communications.sms.providers.AfricasTalkingSmsProvider.send", return_value=ProviderResult(False, "FAILED", error="InsufficientBalance")):
            sms = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "k6", now=self.noon())
        self.assertEqual(sms.delivery_status, "FAILED")
        self.assertEqual(sms.failure_reason, "InsufficientBalance")
        with mock.patch("communications.sms.providers.AfricasTalkingSmsProvider.send", return_value=ProviderResult(True, "SUBMITTED", message_id="ATXid_1")):
            sms_services.process_queue()
        sms.refresh_from_db()
        self.assertEqual(sms.delivery_status, "SUBMITTED")  # accepted ≠ delivered
        self.assertEqual(sms.attempts, 2)

    @override_settings(SMS_PROVIDER="africastalking", AFRICASTALKING_API_KEY="test-key")
    def test_delivery_callback_marks_delivered_idempotently(self):
        self.prefs(self.caregiver)
        with mock.patch("communications.sms.providers.AfricasTalkingSmsProvider.send", return_value=ProviderResult(True, "SUBMITTED", message_id="ATXid_9")):
            sms = sms_services.send_discreet_sms(self.caregiver, "CASE_UPDATE", "k7", now=self.noon())
        c = APIClient()
        for _ in range(2):
            self.assertEqual(c.post("/api/communications/sms/delivery-callback/", {"id": "ATXid_9", "status": "Success"}).status_code, 200)
        sms.refresh_from_db()
        self.assertEqual(sms.delivery_status, "DELIVERED")
        self.assertIsNotNone(sms.delivered_at)

    def test_notify_creates_sms_for_sms_users_only(self):
        self.prefs(self.caregiver)
        notify(self.caregiver, "CASE_UPDATE", dedup_key="n1")
        notify(self.other_caregiver, "CASE_UPDATE", dedup_key="n1")
        self.assertEqual(SmsMessage.objects.count(), 1)

    def test_sms_dashboard_access(self):
        self.assertEqual(self.client_for(self.admin).get("/api/communications/sms/dashboard/").status_code, 200)
        self.assertEqual(self.client_for(self.caregiver).get("/api/communications/sms/dashboard/").status_code, 403)
