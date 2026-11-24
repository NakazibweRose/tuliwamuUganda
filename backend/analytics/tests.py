from django.test import override_settings

from core.testing import World


class AnalyticsTests(World):
    def test_access_limited_to_admin_and_supervisors(self):
        self.assertEqual(self.client_for(self.admin).get("/api/analytics/overview/").status_code, 200)
        self.assertEqual(self.client_for(self.police2).get("/api/analytics/overview/").status_code, 200)  # supervisor
        self.assertEqual(self.client_for(self.police).get("/api/analytics/overview/").status_code, 403)
        self.assertEqual(self.client_for(self.caregiver).get("/api/analytics/overview/").status_code, 403)

    def test_small_cells_are_suppressed(self):
        data = self.client_for(self.admin).get("/api/analytics/overview/").data
        self.assertEqual(data["totals"]["cases"], {"value": None, "suppressed": True})  # only one case
        cat = {c["key"]: c for c in data["cases_by_category"]}
        self.assertTrue(cat["SEXUAL_ABUSE"]["suppressed"])
        self.assertEqual(cat["NEGLECT"]["value"], 0)

    def test_large_cells_are_shown(self):
        for i in range(5):
            self.register(self.police, pseudonym=f"C{i}", category="NEGLECT")
        data = self.client_for(self.admin).get("/api/analytics/overview/").data
        cat = {c["key"]: c for c in data["cases_by_category"]}
        self.assertEqual(cat["NEGLECT"]["value"], 5)
        self.assertEqual(data["totals"]["cases"]["value"], 6)

    def test_no_identifying_data_in_any_report(self):
        for i in range(6):
            self.register(self.police, pseudonym=f"Child {i}")
        c = self.client_for(self.admin)
        blob = str(c.get("/api/analytics/overview/").data) + str(c.get("/api/analytics/referrals/").data) + str(c.get("/api/analytics/case-progress/").data)
        self.assertNotIn(self.case.reference, blob)
        self.assertNotIn("Test Child", blob)
        self.assertNotIn("SECRET", blob)
        self.assertNotIn(str(self.case.id), blob)
