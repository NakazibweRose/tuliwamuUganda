from cases import services as case_services
from cases.models import BeneficiaryStatus, CaseUpdate
from core.testing import World
from notifications.models import Notification
from support_services.models import AssistanceRequest


class GrantSafeguardTests(World):
    def grant(self, user=None, who=None, rel="CAREGIVER", **kw):
        body = {"case_id": str(self.case.id), "username": (who or self.caregiver).username, "relationship": rel,
                "basis": "Caregiver assessed by probation", "conflict_check_confirmed": True}
        body.update(kw)
        return self.client_for(user or self.police).post("/api/access-grants/", body, format="json")

    def test_caregiver_has_no_access_without_grant(self):
        c = self.client_for(self.caregiver)
        self.assertEqual(c.get("/api/beneficiary/cases/").data, [])
        self.assertEqual(c.get(f"/api/beneficiary/cases/{self.case.id}/").status_code, 404)
        self.assertEqual(c.get(f"/api/beneficiary/cases/{self.case.id}/updates/").status_code, 404)

    def test_grant_requires_conflict_check_and_second_officer(self):
        self.assertEqual(self.grant(conflict_check_confirmed=False).status_code, 400)
        r = self.grant()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["status"], "PENDING")
        # Pending grants give no access.
        self.assertEqual(self.client_for(self.caregiver).get("/api/beneficiary/cases/").data, [])
        # Creator cannot approve own grant.
        self.assertEqual(self.client_for(self.police).post(f"/api/access-grants/{r.data['id']}/approve/").status_code, 403)
        ok = self.client_for(self.police2).post(f"/api/access-grants/{r.data['id']}/approve/")
        self.assertEqual(ok.data["status"], "ACTIVE")
        self.assertEqual(len(self.client_for(self.caregiver).get("/api/beneficiary/cases/").data), 1)

    def test_child_self_access_only_for_older_children(self):
        young = self.register(self.police, pseudonym="Young Child", age="5-8")
        r = self.client_for(self.police).post("/api/access-grants/", {
            "case_id": str(young.id), "username": self.child_user.username, "relationship": "SELF",
            "basis": "x", "conflict_check_confirmed": True}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.grant(who=self.child_user, rel="SELF").status_code, 201)

    def test_medical_or_outsider_cannot_grant(self):
        self.assertEqual(self.grant(user=self.gulu_police).status_code, 404)
        self.assertEqual(self.grant(user=self.medic).status_code, 404)

    def test_grant_for_one_case_does_not_open_other_cases_of_same_child(self):
        g = case_services.create_grant(self.police, self.case, self.caregiver, {"relationship": "CAREGIVER", "basis": "x", "conflict_check_confirmed": True})
        case_services.approve_grant(self.police2, g)
        second = case_services.register_case(self.police, {
            "child": self.case.child, "date_reported": self.case.date_reported, "incident_category": "NEGLECT",
            "district": "Kampala", "region": "CENTRAL", "confirm_not_duplicate": True})
        c = self.client_for(self.caregiver)
        ids = [x["id"] for x in c.get("/api/beneficiary/cases/").data]
        self.assertEqual(ids, [str(self.case.id)])
        self.assertEqual(c.get(f"/api/beneficiary/cases/{second.id}/").status_code, 404)

    def test_revoked_grant_removes_access(self):
        g = case_services.create_grant(self.police, self.case, self.caregiver, {"relationship": "CAREGIVER", "basis": "x", "conflict_check_confirmed": True})
        case_services.approve_grant(self.police2, g)
        self.assertEqual(self.client_for(self.police).post(f"/api/access-grants/{g.id}/revoke/", {}, format="json").status_code, 400)
        self.client_for(self.police).post(f"/api/access-grants/{g.id}/revoke/", {"reason": "Safeguarding concern"}, format="json")
        self.assertEqual(self.client_for(self.caregiver).get(f"/api/beneficiary/cases/{self.case.id}/").status_code, 404)


class BeneficiaryViewTests(World):
    def setUp(self):
        super().setUp()
        g = case_services.create_grant(self.police, self.case, self.caregiver, {"relationship": "CAREGIVER", "basis": "x", "conflict_check_confirmed": True})
        case_services.approve_grant(self.police2, g)
        self.c = self.client_for(self.caregiver)

    def test_only_approved_messages_are_visible(self):
        upd = case_services.add_update(self.police, self.case, {"note": "INVESTIGATION-DETAIL", "beneficiary_message": "Your case is moving forward."})
        texts = str(self.c.get(f"/api/beneficiary/cases/{self.case.id}/updates/").data)
        self.assertNotIn("moving forward", texts)  # pending
        self.assertNotIn("INVESTIGATION-DETAIL", texts)
        # The author cannot approve their own message.
        self.assertEqual(self.client_for(self.police).post(f"/api/case-updates/{upd.id}/review/", {"approve": True}, format="json").status_code, 403)
        self.client_for(self.police2).post(f"/api/case-updates/{upd.id}/review/", {"approve": True}, format="json")
        texts = str(self.c.get(f"/api/beneficiary/cases/{self.case.id}/updates/").data)
        self.assertIn("moving forward", texts)
        self.assertNotIn("INVESTIGATION-DETAIL", texts)
        self.assertTrue(Notification.objects.filter(recipient=self.caregiver, type="CASE_UPDATE").exists())

    def test_beneficiary_never_sees_confidential_material(self):
        ref = self.refer(self.police, self.case, self.hospital, visible_to_beneficiary=True)
        m = self.client_for(self.medic)
        m.post(f"/api/referrals/{ref.id}/acknowledge/")
        m.post(f"/api/referrals/{ref.id}/complete/", {"outcome_summary": "OUTCOME-SUMMARY", "restricted_notes": "CLINICAL-NOTES"}, format="json")
        for upd in CaseUpdate.objects.filter(case=self.case, beneficiary_status=BeneficiaryStatus.PENDING):
            case_services.review_update(self.police2, upd, True)
        blob = ""
        for path in ("", "updates/", "appointments/", "services/"):
            r = self.c.get(f"/api/beneficiary/cases/{self.case.id}/{path}")
            self.assertEqual(r.status_code, 200)
            blob += str(r.data)
        for secret in ("SECRET-CONCERN", "SECRET-LOCATION", "CLINICAL-NOTES", "OUTCOME-SUMMARY", "SEXUAL_ABUSE", "Test Child A"):
            self.assertNotIn(secret, blob)
        self.assertIn("medical", blob.lower())

    def test_beneficiary_cannot_use_institutional_endpoints(self):
        for path in ("/api/cases/", f"/api/cases/{self.case.id}/", "/api/referrals/", "/api/appointments/",
                     "/api/analytics/overview/", "/api/anonymous-reports/", "/api/follow-ups/"):
            self.assertEqual(self.c.get(path).status_code, 403, path)

    def test_institutional_user_cannot_use_beneficiary_portal(self):
        self.assertEqual(self.client_for(self.police).get("/api/beneficiary/cases/").status_code, 403)

    def test_assistance_request_reaches_officer_and_is_tracked(self):
        r = self.c.post("/api/beneficiary/assistance-requests/", {"case_id": str(self.case.id), "request_type": "CALL_BACK",
                                                                   "message": "Please call after school"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        req = AssistanceRequest.objects.get(pk=r.data["id"])
        self.assertEqual(req.assigned_to, self.police)
        self.assertTrue(req.follow_ups.filter(status="PENDING").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.police, type="ASSISTANCE_REQUEST").exists())
        officer = self.client_for(self.police)
        self.assertEqual(officer.get("/api/assistance-requests/").data["count"], 1)
        resp = officer.post(f"/api/assistance-requests/{req.id}/respond/", {"status": "RESOLVED", "response_message": "We will call on Friday."}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(req.follow_ups.filter(status="PENDING").exists())
        mine = self.c.get("/api/beneficiary/assistance-requests/").data
        self.assertEqual(mine[0]["response_message"], "We will call on Friday.")

    def test_cannot_request_assistance_on_ungranted_case(self):
        other = self.register(self.police, pseudonym="Other")
        r = self.c.post("/api/beneficiary/assistance-requests/", {"case_id": str(other.id), "request_type": "CALL_BACK"}, format="json")
        self.assertEqual(r.status_code, 404)
