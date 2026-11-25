import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from audit.models import AuditLog
from core.testing import World
from documents.models import CaseDocument
from notifications.models import Notification

PDF = b"%PDF-1.4\n% fictional medical report SECRET-CLINICAL\n%%EOF"


def pdf(name="report.pdf", body=PDF):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<x/>")
        z.writestr("word/document.xml", "<w:document/>")
    return SimpleUploadedFile("police-file.docx", buf.getvalue(), content_type="application/octet-stream")


class DocumentAccessTests(World):
    def setUp(self):
        super().setUp()
        self.medical_ref = self.refer(self.police, self.case, self.hospital, category="MEDICAL")
        self.client_for(self.medic).post(f"/api/referrals/{self.medical_ref.id}/acknowledge/")
        self.odpp_ref = self.refer(self.police, self.case, self.odpp, category="PROSECUTION")
        self.client_for(self.prosecutor).post(f"/api/referrals/{self.odpp_ref.id}/acknowledge/")

    def upload(self, user, referral=None, case=None, file=None, category="MEDICAL_REPORT", **extra):
        body = {"category": category, "title": "Fictional report", "file": file or pdf(), **extra}
        if referral:
            body["referral_id"] = str(referral.id)
        else:
            body["case_id"] = str((case or self.case).id)
        return self.client_for(user).post("/api/documents/", body, format="multipart")

    def test_medical_report_on_referral_reaches_police_only(self):
        r = self.upload(self.medic, referral=self.medical_ref)
        self.assertEqual(r.status_code, 201, r.data)
        doc_id = r.data["id"]
        self.assertEqual(self.client_for(self.police).get(f"/api/documents/{doc_id}/download/").content, PDF)
        for outsider in (self.prosecutor, self.clerk, self.probation_officer, self.gulu_police, self.other_medic):
            self.assertEqual(self.client_for(outsider).get(f"/api/documents/{doc_id}/download/").status_code, 404, outsider.username)
            self.assertEqual(self.client_for(outsider).get("/api/documents/").data, [])
        self.assertTrue(Notification.objects.filter(recipient=self.police, type="DOCUMENT_SHARED").exists())

    def test_beneficiaries_and_admin_never_access_documents(self):
        from cases import services as case_services

        g = case_services.create_grant(self.police, self.case, self.caregiver, {"relationship": "CAREGIVER", "basis": "x", "conflict_check_confirmed": True})
        case_services.approve_grant(self.police2, g)
        doc_id = self.upload(self.medic, referral=self.medical_ref).data["id"]
        for u in (self.caregiver, self.child_user, self.admin):
            c = self.client_for(u)
            self.assertEqual(c.get("/api/documents/").status_code, 403)
            self.assertEqual(c.get(f"/api/documents/{doc_id}/download/").status_code, 403)
        blob = "".join(str(self.client_for(self.caregiver).get(f"/api/beneficiary/cases/{self.case.id}/{p}").data) for p in ("", "updates/", "services/"))
        self.assertNotIn("Fictional report", blob)

    def test_police_forward_medical_report_to_odpp(self):
        doc_id = self.upload(self.medic, referral=self.medical_ref).data["id"]
        p = self.client_for(self.police)
        targets = {t["name"] for t in p.get(f"/api/documents/{doc_id}/share-targets/").data}
        self.assertIn(self.odpp.name, targets)
        self.assertNotIn(self.gulu.name, targets)
        self.assertEqual(p.post(f"/api/documents/{doc_id}/share/", {"institution_id": str(self.odpp.id)}, format="json").status_code, 200)
        self.assertEqual(self.client_for(self.prosecutor).get(f"/api/documents/{doc_id}/download/").content, PDF)
        # It appears on the ODPP referral for both sides, and not on unrelated referrals.
        self.assertEqual([d["id"] for d in self.client_for(self.prosecutor).get(f"/api/documents/?referral={self.odpp_ref.id}").data], [doc_id])
        self.assertIn(doc_id, [d["id"] for d in p.get(f"/api/documents/?referral={self.odpp_ref.id}").data])
        # Not to institutions outside the case.
        self.assertEqual(p.post(f"/api/documents/{doc_id}/share/", {"institution_id": str(self.gulu.id)}, format="json").status_code, 400)
        self.assertTrue(AuditLog.objects.filter(action="document.share", is_security_event=True).exists())

    def test_non_forwardable_document_cannot_be_forwarded_by_recipient(self):
        doc_id = self.upload(self.medic, referral=self.medical_ref, forwardable="false").data["id"]
        r = self.client_for(self.police).post(f"/api/documents/{doc_id}/share/", {"institution_id": str(self.odpp.id)}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client_for(self.police).get(f"/api/documents/{doc_id}/share-targets/").data, [])

    def test_police_file_to_odpp_on_prosecution_referral(self):
        r = self.upload(self.police, referral=self.odpp_ref, file=docx(), category="POLICE_FILE")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["mime_type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertEqual(self.client_for(self.prosecutor).get(f"/api/documents/{r.data['id']}/download/").status_code, 200)
        self.assertEqual(self.client_for(self.medic).get(f"/api/documents/{r.data['id']}/download/").status_code, 404)

    def test_internal_case_document_stays_inside_institution(self):
        doc_id = self.upload(self.police, category="STATEMENT").data["id"]
        self.assertEqual(self.client_for(self.police2).get(f"/api/documents/{doc_id}/download/").status_code, 200)
        self.assertEqual(self.client_for(self.medic).get(f"/api/documents/{doc_id}/download/").status_code, 404)
        self.assertEqual(self.client_for(self.prosecutor).get(f"/api/documents/{doc_id}/download/").status_code, 404)

    def test_outsiders_cannot_upload(self):
        self.assertEqual(self.upload(self.gulu_police).status_code, 404)
        self.assertEqual(self.upload(self.clerk, referral=self.medical_ref).status_code, 404)

    def test_files_are_validated_by_content(self):
        fake = SimpleUploadedFile("report.pdf", b"<script>alert(1)</script>", content_type="application/pdf")
        self.assertEqual(self.upload(self.medic, referral=self.medical_ref, file=fake).status_code, 400)
        exe = SimpleUploadedFile("x.pdf", b"MZ\x90\x00", content_type="application/pdf")
        self.assertEqual(self.upload(self.medic, referral=self.medical_ref, file=exe).status_code, 400)
        big = SimpleUploadedFile("big.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024), content_type="application/pdf")
        self.assertEqual(self.upload(self.medic, referral=self.medical_ref, file=big).status_code, 400)
        self.assertEqual(self.upload(self.medic, referral=self.medical_ref, category="NOPE").status_code, 400)

    def test_stored_encrypted_and_downloads_are_safe_and_audited(self):
        r = self.upload(self.medic, referral=self.medical_ref, file=pdf(name='../../etc/"evil".pdf'))
        with connection.cursor() as cur:
            cur.execute("SELECT data FROM documents_casedocument")
            self.assertNotIn(b"SECRET-CLINICAL", bytes(cur.fetchone()[0]))
        resp = self.client_for(self.police).get(f"/api/documents/{r.data['id']}/download/")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertNotIn("..", resp["Content-Disposition"])
        self.assertNotIn('"evil"', resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "no-store, private")
        self.assertTrue(AuditLog.objects.filter(action="document.download", is_security_event=True).exists())

    def test_withdraw_destroys_content_and_only_owner_can(self):
        doc_id = self.upload(self.medic, referral=self.medical_ref).data["id"]
        self.assertEqual(self.client_for(self.police).post(f"/api/documents/{doc_id}/withdraw/", {"reason": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client_for(self.medic).post(f"/api/documents/{doc_id}/withdraw/", {}, format="json").status_code, 400)
        self.assertEqual(self.client_for(self.medic).post(f"/api/documents/{doc_id}/withdraw/", {"reason": "Wrong case"}, format="json").status_code, 204)
        self.assertEqual(self.client_for(self.police).get(f"/api/documents/{doc_id}/download/").status_code, 404)
        self.assertEqual(bytes(CaseDocument.objects.get(pk=doc_id).data), b"")

    def test_only_owner_sees_sharing_list(self):
        doc_id = self.upload(self.medic, referral=self.medical_ref).data["id"]
        mine = self.client_for(self.medic).get("/api/documents/").data[0]
        theirs = self.client_for(self.police).get("/api/documents/").data[0]
        self.assertEqual(mine["shared_with"], [self.kla.name])
        self.assertIsNone(theirs["shared_with"])
        self.assertEqual(theirs["id"], doc_id)
