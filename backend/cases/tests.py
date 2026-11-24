from datetime import timedelta

from django.db import connection
from django.utils import timezone

from cases.models import BeneficiaryStatus, CaseStatusHistory, CaseUpdate, ChildCase
from core.testing import World


class CaseRegistrationTests(World):
    def payload(self, **kw):
        p = {"child_pseudonym": "Demo Child Z", "age_range": "9-11", "date_reported": str(timezone.localdate()),
             "incident_category": "NEGLECT", "district": "Kampala", "region": "CENTRAL", "referral_needs": ["MEDICAL"]}
        p.update(kw)
        return p

    def test_police_registers_case_with_reference_history_and_team(self):
        r = self.client_for(self.police).post("/api/cases/", self.payload(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertRegex(r.data["reference"], r"^TLW-\d{4}-[A-Z2-9]{6}$")
        case = ChildCase.objects.get(pk=r.data["id"])
        self.assertEqual(case.stage_id, "REPORT_RECEIVED")
        self.assertEqual(CaseStatusHistory.objects.filter(case=case).count(), 1)
        self.assertTrue(case.assignments.filter(institution=self.kla, is_lead=True).exists())
        self.assertEqual(case.assigned_officer, self.police)

    def test_duplicate_case_requires_confirmation(self):
        c = self.client_for(self.police)
        first = c.post("/api/cases/", self.payload(), format="json")
        dup = c.post("/api/cases/", self.payload(child_id=first.data["child_id"], child_pseudonym=""), format="json")
        self.assertEqual(dup.status_code, 400)
        self.assertIn("duplicate_warning", dup.data["error"]["details"])
        ok = c.post("/api/cases/", self.payload(child_id=first.data["child_id"], confirm_not_duplicate=True), format="json")
        self.assertEqual(ok.status_code, 201)
        # One child, many cases.
        self.assertEqual(ChildCase.objects.filter(child_id=first.data["child_id"]).count(), 2)

    def test_validation(self):
        c = self.client_for(self.police)
        future = str(timezone.localdate() + timedelta(days=2))
        self.assertEqual(c.post("/api/cases/", self.payload(date_reported=future), format="json").status_code, 400)
        self.assertEqual(c.post("/api/cases/", self.payload(incident_category="MURDER"), format="json").status_code, 400)
        r = c.post("/api/cases/", self.payload(child_pseudonym=""), format="json")
        self.assertEqual(r.status_code, 400)

    def test_non_registering_roles_cannot_register(self):
        for u in (self.medic, self.prosecutor, self.clerk):
            self.assertEqual(self.client_for(u).post("/api/cases/", self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client_for(self.caregiver).post("/api/cases/", self.payload(), format="json").status_code, 403)

    def test_cannot_link_unknown_child(self):
        other = self.register(self.gulu_police, pseudonym="Gulu Child")
        r = self.client_for(self.police).post("/api/cases/", self.payload(child_id=str(other.child_id)), format="json")
        self.assertEqual(r.status_code, 400)

    def test_assigned_officer_must_be_same_institution(self):
        r = self.client_for(self.police).post("/api/cases/", self.payload(assigned_officer_id=str(self.gulu_police.id)), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client_for(self.police).post("/api/cases/", self.payload(assigned_officer_id=str(self.police2.id)), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["assigned_officer"]["id"], str(self.police2.id))

    def test_sensitive_fields_are_encrypted_at_rest(self):
        with connection.cursor() as cur:
            cur.execute("SELECT protection_concerns FROM cases_childcase WHERE id = %s", [self.case.id])
            raw = cur.fetchone()[0]
        self.assertTrue(raw.startswith("enc1:"))
        self.assertNotIn("SECRET-CONCERN", raw)
        self.assertEqual(ChildCase.objects.get(pk=self.case.pk).protection_concerns, "SECRET-CONCERN fictional")


class IsolationTests(World):
    def test_other_institution_cannot_access_case_by_changing_id(self):
        c = self.client_for(self.gulu_police)
        self.assertEqual(c.get(f"/api/cases/{self.case.id}/").status_code, 404)
        self.assertEqual(c.get(f"/api/cases/{self.case.id}/timeline/").status_code, 404)
        self.assertEqual(c.patch(f"/api/cases/{self.case.id}/", {"district": "X"}, format="json").status_code, 404)
        self.assertNotIn(str(self.case.id), str(c.get("/api/cases/").data))

    def test_medical_officer_cannot_access_unrelated_investigation_file(self):
        c = self.client_for(self.medic)
        self.assertEqual(c.get(f"/api/cases/{self.case.id}/").status_code, 404)
        self.assertEqual(c.get("/api/cases/").data["count"], 0)

    def test_referral_recipient_sees_only_snapshot_until_acknowledged(self):
        ref = self.refer(self.police, self.case, self.hospital)
        c = self.client_for(self.medic)
        r = c.get(f"/api/referrals/{ref.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.data["shared_data"]), {"age_range", "incident_category"})
        self.assertNotIn("SECRET-CONCERN", str(r.data))
        self.assertFalse(r.data["case_on_team"])
        self.assertEqual(c.get(f"/api/cases/{self.case.id}/").status_code, 404)
        c.post(f"/api/referrals/{ref.id}/acknowledge/")
        detail = c.get(f"/api/cases/{self.case.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data["sensitive"])  # team member but not lead
        self.assertNotIn("SECRET-LOCATION", str(detail.data))

    def test_lead_sees_sensitive_fields(self):
        r = self.client_for(self.police).get(f"/api/cases/{self.case.id}/")
        self.assertEqual(r.data["sensitive"]["protection_concerns"], "SECRET-CONCERN fictional")

    def test_internal_notes_stay_inside_institution(self):
        ref = self.refer(self.police, self.case, self.hospital)
        self.client_for(self.medic).post(f"/api/referrals/{ref.id}/acknowledge/")
        self.client_for(self.police).post(f"/api/cases/{self.case.id}/updates/",
                                          {"note": "POLICE-ONLY-NOTE", "visibility": "INTERNAL"}, format="json")
        medic_timeline = self.client_for(self.medic).get(f"/api/cases/{self.case.id}/timeline/")
        self.assertNotIn("POLICE-ONLY-NOTE", str(medic_timeline.data))
        police_timeline = self.client_for(self.police).get(f"/api/cases/{self.case.id}/timeline/")
        self.assertIn("POLICE-ONLY-NOTE", str(police_timeline.data))

    def test_only_lead_edits_core_details(self):
        ref = self.refer(self.police, self.case, self.hospital)
        self.client_for(self.medic).post(f"/api/referrals/{ref.id}/acknowledge/")
        self.assertEqual(self.client_for(self.medic).patch(f"/api/cases/{self.case.id}/", {"district": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client_for(self.police).patch(f"/api/cases/{self.case.id}/", {"district": "Wakiso"}, format="json").status_code, 200)


class StageTests(World):
    def test_stage_change_is_role_restricted_and_recorded(self):
        c = self.client_for(self.police)
        r = c.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "UNDER_INVESTIGATION"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["stage"]["code"], "UNDER_INVESTIGATION")
        self.assertEqual(c.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "COURT_HEARING_SCHEDULED"}, format="json").status_code, 403)
        hist = c.get(f"/api/cases/{self.case.id}/history/").data
        self.assertEqual([h["to_stage"] for h in hist], ["Report received", "Under investigation"])

    def test_stage_change_is_not_shown_to_beneficiary_automatically(self):
        self.client_for(self.police).post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "UNDER_INVESTIGATION"}, format="json")
        stage_update = CaseUpdate.objects.filter(case=self.case, category="STAGE_CHANGE").get()
        self.assertEqual(stage_update.beneficiary_status, BeneficiaryStatus.NONE)
