from notifications.models import Notification
from referrals.models import Referral, ReferralStatusHistory
from cases.models import BeneficiaryStatus, CaseUpdate
from core.testing import World


class ReferralWorkflowTests(World):
    def create(self, user=None, **kw):
        body = {"case_id": str(self.case.id), "receiving_institution_id": str(self.hospital.id), "category": "MEDICAL",
                "priority": "URGENT", "purpose": "Examination and care", "shared_fields": ["age_range", "immediate_risk"]}
        body.update(kw)
        return self.client_for(user or self.police).post("/api/referrals/", body, format="json")

    def test_medical_referral_full_lifecycle(self):
        r = self.create(visible_to_beneficiary=True)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["status"], "SENT")
        rid = r.data["id"]
        self.assertTrue(Notification.objects.filter(recipient=self.medic, type="REFERRAL_RECEIVED").exists())

        medic = self.client_for(self.medic)
        self.assertEqual(medic.get("/api/referrals/?direction=incoming").data["count"], 1)
        self.assertEqual(medic.post(f"/api/referrals/{rid}/acknowledge/").data["status"], "ACKNOWLEDGED")
        self.assertTrue(Notification.objects.filter(recipient=self.police, type="REFERRAL_ACKNOWLEDGED").exists())
        self.assertEqual(medic.post(f"/api/referrals/{rid}/start/").data["status"], "IN_PROGRESS")
        bad = medic.post(f"/api/referrals/{rid}/complete/", {}, format="json")
        self.assertEqual(bad.status_code, 400)
        done = medic.post(f"/api/referrals/{rid}/complete/", {"outcome_summary": "Examined and treated.",
                                                               "restricted_notes": "CLINICAL-DETAIL"}, format="json")
        self.assertEqual(done.data["status"], "COMPLETED")
        ref = Referral.objects.get(pk=rid)
        self.assertIsNotNone(ref.acknowledged_at)
        self.assertIsNotNone(ref.completed_at)
        self.assertEqual(
            list(ReferralStatusHistory.objects.filter(referral=ref).values_list("to_status", flat=True)),
            ["DRAFT", "SENT", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED"],
        )
        # A family-facing milestone is proposed but NOT visible until a reviewer approves it.
        pending = CaseUpdate.objects.filter(case=self.case, beneficiary_status=BeneficiaryStatus.PENDING)
        self.assertTrue(pending.filter(beneficiary_message__icontains="medical").exists())

    def test_restricted_notes_only_visible_to_receiving_institution(self):
        rid = self.create().data["id"]
        medic = self.client_for(self.medic)
        medic.post(f"/api/referrals/{rid}/acknowledge/")
        medic.post(f"/api/referrals/{rid}/complete/", {"outcome_summary": "Done", "restricted_notes": "CLINICAL-DETAIL"}, format="json")
        self.assertEqual(medic.get(f"/api/referrals/{rid}/").data["restricted_notes"], "CLINICAL-DETAIL")
        police_view = self.client_for(self.police).get(f"/api/referrals/{rid}/").data
        self.assertIsNone(police_view["restricted_notes"])
        self.assertNotIn("CLINICAL-DETAIL", str(police_view))
        self.assertNotIn("CLINICAL-DETAIL", str(self.client_for(self.police).get(f"/api/cases/{self.case.id}/timeline/").data))

    def test_only_correct_side_can_act(self):
        rid = self.create().data["id"]
        self.assertEqual(self.client_for(self.police).post(f"/api/referrals/{rid}/acknowledge/").status_code, 403)
        self.assertEqual(self.client_for(self.other_medic).post(f"/api/referrals/{rid}/acknowledge/").status_code, 404)
        self.assertEqual(self.client_for(self.medic).post(f"/api/referrals/{rid}/cancel/", {"note": "x"}, format="json").status_code, 403)

    def test_invalid_transitions_rejected(self):
        rid = self.create().data["id"]
        self.assertEqual(self.client_for(self.medic).post(f"/api/referrals/{rid}/complete/", {"outcome_summary": "x"}, format="json").status_code, 400)
        self.assertEqual(self.client_for(self.medic).post(f"/api/referrals/{rid}/decline/", {}, format="json").status_code, 400)

    def test_return_and_resend(self):
        rid = self.create().data["id"]
        self.client_for(self.medic).post(f"/api/referrals/{rid}/return/", {"note": "Please confirm language"}, format="json")
        self.assertEqual(Referral.objects.get(pk=rid).status, "RETURNED")
        r = self.client_for(self.police).post(f"/api/referrals/{rid}/resend/", {"note": "Language is Luganda"}, format="json")
        self.assertEqual(r.data["status"], "SENT")

    def test_receiver_must_match_category(self):
        r = self.create(receiving_institution_id=str(self.court.id))
        self.assertEqual(r.status_code, 400)

    def test_non_lead_cannot_share_sensitive_fields(self):
        rid = self.create().data["id"]
        self.client_for(self.medic).post(f"/api/referrals/{rid}/acknowledge/")
        r = self.client_for(self.medic).post("/api/referrals/", {
            "case_id": str(self.case.id), "receiving_institution_id": str(self.probation.id), "category": "PROBATION",
            "purpose": "Welfare follow-up", "shared_fields": ["protection_concerns"]}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_outsider_cannot_refer_case(self):
        r = self.create(user=self.gulu_police)
        self.assertEqual(r.status_code, 404)

    def test_duplicate_open_referral_blocked(self):
        self.create()
        self.assertEqual(self.create().status_code, 400)

    def test_notifications_never_contain_case_details(self):
        self.create()
        for n in Notification.objects.all():
            text = f"{n.title} {n.body} {n.link}"
            for secret in (self.case.reference, "SEXUAL", "Test Child", "SECRET", "defilement"):
                self.assertNotIn(secret, text)


class ProsecutionAndForensicTests(World):
    def test_forensic_referral_traceable(self):
        ref = self.refer(self.police, self.case, self.forensic, category="FORENSIC")
        c = self.client_for(self.forensic_officer)
        c.post(f"/api/referrals/{ref.id}/acknowledge/")
        c.post(f"/api/referrals/{ref.id}/start/")
        c.post(f"/api/referrals/{ref.id}/complete/", {"outcome_summary": "Analysis complete; report sent through official channel."}, format="json")
        self.assertEqual(len(c.get(f"/api/referrals/{ref.id}/").data["history"]), 5)
        self.assertEqual(c.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "FORENSIC_REFERRAL_COMPLETED"}, format="json").status_code, 200)

    def test_prosecutor_records_review_milestones_and_requests_information(self):
        pc = self.client_for(self.police)
        pc.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "FILE_SUBMITTED_FOR_PROSECUTION"}, format="json")
        ref = self.refer(self.police, self.case, self.odpp, category="PROSECUTION")
        c = self.client_for(self.prosecutor)
        c.post(f"/api/referrals/{ref.id}/acknowledge/")
        r = c.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "AWAITING_ADDITIONAL_INFORMATION", "note": "Need medical form"}, format="json")
        self.assertEqual(r.status_code, 200)
        r = c.post(f"/api/referrals/{ref.id}/return/", {"note": "Please attach outstanding documents"}, format="json")
        self.assertEqual(r.data["status"], "RETURNED")
        pc.post(f"/api/referrals/{ref.id}/resend/", {"note": "Documents attached"}, format="json")
        c.post(f"/api/referrals/{ref.id}/acknowledge/")
        r = c.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "PROSECUTION_DECISION_RECORDED"}, format="json")
        self.assertEqual(r.status_code, 200)
        # Police cannot record a prosecution decision.
        self.assertEqual(pc.post(f"/api/cases/{self.case.id}/change-stage/", {"stage": "PROSECUTION_DECISION_RECORDED"}, format="json").status_code, 403)
