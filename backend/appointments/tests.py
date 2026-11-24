from datetime import timedelta

from django.utils import timezone

from appointments.models import Appointment
from appointments.services import send_due_reminders
from cases import services as case_services
from core.testing import World
from notifications.models import Notification


class AppointmentTests(World):
    def setUp(self):
        super().setUp()
        ref = self.refer(self.police, self.case, self.court, category="COURT")
        self.client_for(self.clerk).post(f"/api/referrals/{ref.id}/acknowledge/")
        g = case_services.create_grant(self.police, self.case, self.caregiver, {"relationship": "CAREGIVER", "basis": "Test", "conflict_check_confirmed": True})
        case_services.approve_grant(self.police2, g)

    def hearing(self, user, days=3):
        return self.client_for(user).post("/api/appointments/", {
            "case_id": str(self.case.id), "type": "COURT_HEARING",
            "scheduled_for": (timezone.now() + timedelta(days=days)).isoformat(),
            "public_location": "Test court room 1", "visible_to_beneficiary": True}, format="json")

    def test_only_court_schedules_hearings(self):
        self.assertEqual(self.hearing(self.police).status_code, 403)
        r = self.hearing(self.clerk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Notification.objects.filter(recipient=self.caregiver, type="APPOINTMENT_SCHEDULED").exists())

    def test_outsider_cannot_schedule(self):
        self.assertEqual(self.hearing(self.gulu_police).status_code, 404)

    def test_reschedule_records_previous_and_notifies(self):
        appt_id = self.hearing(self.clerk).data["id"]
        new_time = (timezone.now() + timedelta(days=9)).isoformat()
        r = self.client_for(self.clerk).patch(f"/api/appointments/{appt_id}/", {"scheduled_for": new_time}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "RESCHEDULED")
        self.assertIsNotNone(r.data["previous_scheduled_for"])
        self.assertTrue(Notification.objects.filter(recipient=self.caregiver, type="APPOINTMENT_CHANGED").exists())

    def test_reminders_sent_once(self):
        self.hearing(self.clerk, days=1)
        self.assertEqual(send_due_reminders(), 1)
        self.assertEqual(send_due_reminders(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.caregiver, type="APPOINTMENT_REMINDER").count(), 1)

    def test_internal_note_hidden_from_other_institutions(self):
        r = self.client_for(self.clerk).post("/api/appointments/", {
            "case_id": str(self.case.id), "type": "COURT_HEARING", "scheduled_for": (timezone.now() + timedelta(days=4)).isoformat(),
            "public_location": "Room", "internal_note": "COURT-INTERNAL"}, format="json")
        police_view = self.client_for(self.police).get(f"/api/cases/{self.case.id}/appointments/").data
        self.assertIsNone(police_view[0]["internal_note"])
        ben = self.client_for(self.caregiver).get(f"/api/beneficiary/cases/{self.case.id}/appointments/").data
        self.assertNotIn("COURT-INTERNAL", str(ben))
