from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings

from cases.models import BeneficiaryAccessGrant
from complaints.models import Complaint, ComplaintAudio
from core.testing import World
from notifications.models import Notification, NotificationPreference
from communications.models import SmsMessage


class FakeSunbird:
    def __init__(self, *a, **k):
        pass

    def transcribe(self, raw, mime, lang):
        return "Muliraano yange akuba muwala wange"

    def translate(self, text, src, tgt):
        return "[translated] " + text

    def triage(self, english):
        return {"category": "PHYSICAL_VIOLENCE", "urgency": "HIGH", "summary": "AI-SUMMARY-SECRET", "key_facts": ["fact"]}


@override_settings(SUNBIRD_API_KEY="test", COMPLAINT_AI_ASYNC=False)
@mock.patch("complaints.ai.SunbirdClient", FakeSunbird)
class ComplaintFlowTests(World):
    def setUp(self):
        super().setUp()
        self.complainant = self.user("complainant", "COMPLAINANT")
        self.c = self.client_for(self.complainant)

    def submit(self, audio=True, **kw):
        body = {"concerning": "MY_CHILD", "child_age_range": "9-11", "district": "Kampala", "language": "lg",
                "reply_language": "lg", "written_statement": "Written part", "ai_consent": "true"}
        body.update(kw)
        if audio:
            body["audio"] = SimpleUploadedFile("v.webm", b"RIFFfakeaudio" * 10, content_type="audio/webm")
        return self.c.post("/api/my/reports/", body, format="multipart")

    def test_submission_runs_ai_and_routes_to_police(self):
        r = self.submit()
        self.assertEqual(r.status_code, 201, r.data)
        comp = Complaint.objects.get(pk=r.data["id"])
        self.assertEqual(comp.status, "AWAITING_VERIFICATION")
        self.assertEqual(comp.ai_status, "DONE")
        self.assertEqual(comp.ai_category, "PHYSICAL_VIOLENCE")
        self.assertEqual(comp.assigned_institution, self.kla)
        self.assertTrue(Notification.objects.filter(recipient=self.complainant, type="COMPLAINT_RECEIVED").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.police, type="NEW_COMPLAINT").exists())

    def test_complainant_never_sees_ai_output_or_transcript(self):
        rid = self.submit().data["id"]
        blob = str(self.c.get(f"/api/my/reports/{rid}/").data) + str(self.c.get("/api/my/reports/").data)
        for secret in ("AI-SUMMARY-SECRET", "Muliraano", "Written part", "PHYSICAL_VIOLENCE", "translated"):
            self.assertNotIn(secret, blob)
        self.assertIn("respond_by", blob)

    def test_audio_is_encrypted_and_police_only(self):
        rid = self.submit().data["id"]
        with connection.cursor() as cur:
            cur.execute("SELECT data FROM complaints_complaintaudio")
            self.assertNotIn(b"RIFFfakeaudio", bytes(cur.fetchone()[0]))
        self.assertEqual(self.client_for(self.police).get(f"/api/complaints/{rid}/audio/").content[:13], b"RIFFfakeaudio")
        self.assertEqual(self.client_for(self.gulu_police).get(f"/api/complaints/{rid}/audio/").status_code, 404)
        self.assertEqual(self.c.get(f"/api/complaints/{rid}/audio/").status_code, 403)
        self.assertEqual(self.client_for(self.medic).get(f"/api/complaints/{rid}/").status_code, 403)

    def test_other_complainants_cannot_see_report(self):
        rid = self.submit().data["id"]
        other = self.client_for(self.user("other", "COMPLAINANT"))
        self.assertEqual(other.get(f"/api/my/reports/{rid}/").status_code, 404)
        self.assertEqual(other.get("/api/my/reports/").data, [])

    def test_police_question_reply_register_and_follow(self):
        rid = self.submit().data["id"]
        p = self.client_for(self.police)
        r = p.post(f"/api/complaints/{rid}/message/", {"text": "How old is your daughter?", "needs_info": True}, format="json")
        self.assertEqual(r.data["status"], "NEEDS_INFO")
        mine = self.c.get(f"/api/my/reports/{rid}/").data
        self.assertEqual(mine["messages"][0]["text"], "[translated] How old is your daughter?")  # in complainant's language
        self.c.post(f"/api/my/reports/{rid}/reply/", {"text": "Ali wa myaka mwenda"}, format="json")
        self.assertEqual(Complaint.objects.get(pk=rid).status, "AWAITING_VERIFICATION")
        r = p.post(f"/api/complaints/{rid}/register/", {"child_pseudonym": "Demo Child R", "age_range": "9-11",
                   "incident_category": "PHYSICAL_VIOLENCE", "district": "Kampala", "region": "CENTRAL"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "REGISTERED")
        case_id = r.data["case"]["id"]
        self.assertTrue(BeneficiaryAccessGrant.objects.filter(case_id=case_id, user=self.complainant, status="ACTIVE").exists())
        mine = self.c.get(f"/api/my/reports/{rid}/").data
        self.assertEqual(mine["case"]["id"], case_id)
        self.assertEqual(len(self.c.get("/api/beneficiary/cases/").data), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.complainant, type="COMPLAINT_REGISTERED").exists())
        # Decided reports cannot be registered twice.
        self.assertEqual(p.post(f"/api/complaints/{rid}/register/", {"child_pseudonym": "x", "age_range": "9-11",
                         "incident_category": "OTHER", "district": "K", "region": "CENTRAL"}, format="json").status_code, 400)

    def test_late_reply_never_undoes_a_police_decision(self):
        from complaints import services
        from complaints.models import Complaint as C

        rid = self.submit().data["id"]
        self.client_for(self.police).post(f"/api/complaints/{rid}/message/", {"text": "Question?", "needs_info": True}, format="json")
        stale = C.objects.get(pk=rid)  # complainant's request loaded the report before the officer decided
        self.client_for(self.police).post(f"/api/complaints/{rid}/register/", {"child_pseudonym": "x", "age_range": "9-11",
            "incident_category": "OTHER", "district": "Kampala", "region": "CENTRAL"}, format="json")
        services.complainant_reply(self.complainant, stale, "Late answer")
        self.assertEqual(C.objects.get(pk=rid).status, "REGISTERED")

    def test_reporter_of_another_child_cannot_follow_that_case(self):
        rid = self.submit(concerning="OTHER_CHILD").data["id"]
        r = self.client_for(self.police).post(f"/api/complaints/{rid}/register/", {"child_pseudonym": "Neighbour child",
                 "age_range": "5-8", "incident_category": "NEGLECT", "district": "Kampala", "region": "CENTRAL"}, format="json")
        self.assertEqual(r.data["status"], "REGISTERED")
        self.assertFalse(BeneficiaryAccessGrant.objects.filter(user=self.complainant).exists())
        self.assertIsNone(self.c.get(f"/api/my/reports/{rid}/").data["case"])
        self.assertEqual(self.c.get("/api/beneficiary/cases/").data, [])

    def test_only_assigned_station_police_can_decide(self):
        rid = self.submit().data["id"]
        body = {"child_pseudonym": "x", "age_range": "9-11", "incident_category": "OTHER", "district": "K", "region": "CENTRAL"}
        self.assertEqual(self.client_for(self.gulu_police).post(f"/api/complaints/{rid}/register/", body, format="json").status_code, 404)
        self.assertEqual(self.client_for(self.probation_officer).get("/api/complaints/").status_code, 403)
        self.assertEqual(self.client_for(self.admin).get("/api/complaints/").status_code, 403)

    def test_decline_requires_message_to_complainant(self):
        rid = self.submit().data["id"]
        p = self.client_for(self.police)
        self.assertEqual(p.post(f"/api/complaints/{rid}/decline/", {}, format="json").status_code, 400)
        r = p.post(f"/api/complaints/{rid}/decline/", {"message": "Please visit the probation office.", "internal_note": "INTERNAL-X"}, format="json")
        self.assertEqual(r.data["status"], "NOT_REGISTERED")
        self.assertNotIn("INTERNAL-X", str(self.c.get(f"/api/my/reports/{rid}/").data))

    def test_district_routing(self):
        rid = self.submit(district="gulu").data["id"]
        self.assertEqual(Complaint.objects.get(pk=rid).assigned_institution, self.gulu)

    def test_validation(self):
        self.assertEqual(self.submit(audio=False, written_statement="").status_code, 400)
        bad = self.submit(audio=False)
        self.assertEqual(bad.status_code, 201)
        r = self.c.post("/api/my/reports/", {"concerning": "SELF", "district": "Kampala", "language": "en",
                        "audio": SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_institutional_users_cannot_file_through_portal(self):
        self.assertEqual(self.client_for(self.police).get("/api/my/reports/").status_code, 403)

    def test_sms_for_complaints_is_generic(self):
        NotificationPreference.objects.create(user=self.complainant, preferred_channel="SMS", sms_consent=True,
                                              safe_phone="0772000123", consent_reference="T", quiet_hours_start=0, quiet_hours_end=0)
        self.submit()
        sms = SmsMessage.objects.get(recipient=self.complainant)
        self.assertNotIn("report", sms.body.lower())
        self.assertNotIn("police", sms.body.lower())


@override_settings(SUNBIRD_API_KEY="", COMPLAINT_AI_ASYNC=False)
class ComplaintWithoutAiTests(World):
    def test_report_still_reaches_police_when_ai_unavailable(self):
        u = self.user("complainant", "COMPLAINANT")
        r = self.client_for(u).post("/api/my/reports/", {"concerning": "SELF", "district": "Kampala", "language": "en",
                                    "written_statement": "My uncle beats me", "ai_consent": "true"}, format="multipart")
        c = Complaint.objects.get(pk=r.data["id"])
        self.assertEqual(c.status, "AWAITING_VERIFICATION")
        self.assertEqual(c.ai_status, "SKIPPED")
        self.assertEqual(c.ai_category, "PHYSICAL_VIOLENCE")  # keyword fallback, labelled
        self.assertIn("keyword", c.ai_model)

    def test_no_consent_means_no_ai(self):
        u = self.user("complainant", "COMPLAINANT")
        with override_settings(SUNBIRD_API_KEY="x"), mock.patch("complaints.ai.SunbirdClient") as client:
            self.client_for(u).post("/api/my/reports/", {"concerning": "SELF", "district": "Kampala", "language": "lg",
                                    "written_statement": "text", "ai_consent": "false"}, format="multipart")
            client.assert_not_called()
