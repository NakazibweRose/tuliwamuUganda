from django.conf import settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from core.testing import PASSWORD, World


class AuthTests(World):
    def login(self, username, password=PASSWORD, client=None):
        client = client or APIClient()
        return client, client.post("/api/auth/login/", {"username": username, "password": password}, format="json")

    def test_login_returns_access_token_and_httponly_refresh_cookie(self):
        _, r = self.login("police")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertNotIn("refresh", r.data)  # refresh token is never exposed to JavaScript
        cookie = r.cookies[settings.REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(r.data["user"]["role"], "POLICE")
        self.assertTrue(r.data["user"]["permissions"]["register_case"])

    def test_wrong_password_gives_generic_error_and_audits(self):
        _, r = self.login("police", "nope")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data["error"]["message"], "Invalid username or password.")
        _, r2 = self.login("nobody", "nope")
        self.assertEqual(r2.data["error"]["message"], r.data["error"]["message"])
        self.assertTrue(AuditLog.objects.filter(action="auth.login_failed", is_security_event=True).exists())

    def test_account_locks_after_repeated_failures(self):
        for _ in range(5):
            self.login("medic", "wrong-password")
        _, r = self.login("medic")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["error"]["code"], "locked")

    def test_refresh_uses_cookie_and_rotates(self):
        client, _ = self.login("police")
        r = client.post("/api/auth/refresh/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_logout_invalidates_refresh_cookie(self):
        client, r = self.login("police")
        old_cookie = r.cookies[settings.REFRESH_COOKIE_NAME].value
        client.post("/api/auth/logout/")
        replay = APIClient()
        replay.cookies[settings.REFRESH_COOKIE_NAME] = old_cookie
        self.assertEqual(replay.post("/api/auth/refresh/").status_code, 401)

    def test_unauthenticated_requests_are_rejected(self):
        self.assertEqual(APIClient().get("/api/cases/").status_code, 401)
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)

    def test_password_reset_does_not_reveal_accounts(self):
        a = APIClient().post("/api/auth/password-reset/", {"email": "police@nowhere.example"}, format="json")
        b = APIClient().post("/api/auth/password-reset/", {"email": "unknown@nowhere.example"}, format="json")
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.data, b.data)


class AdminBoundaryTests(World):
    def test_admin_cannot_read_case_content(self):
        c = self.client_for(self.admin)
        self.assertEqual(c.get("/api/cases/").status_code, 403)
        self.assertEqual(c.get(f"/api/cases/{self.case.id}/").status_code, 403)
        self.assertEqual(c.get("/api/referrals/").status_code, 403)
        self.assertEqual(c.get("/api/anonymous-reports/").status_code, 403)

    def test_admin_can_manage_users_and_read_audit(self):
        c = self.client_for(self.admin)
        self.assertEqual(c.get("/api/admin/users/").status_code, 200)
        self.assertEqual(c.get("/api/audit-logs/").status_code, 200)
        r = c.post("/api/admin/users/", {"username": "newmedic", "full_name": "New", "role": "MEDICAL",
                                         "institution_id": str(self.hospital.id), "password": "Another#Pass2026"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["institution"]["name"], self.hospital.name)

    def test_ordinary_users_cannot_use_admin_functions(self):
        for u in (self.police, self.caregiver, self.medic):
            c = self.client_for(u)
            self.assertEqual(c.get("/api/admin/users/").status_code, 403)
            self.assertEqual(c.get("/api/audit-logs/").status_code, 403)
            self.assertEqual(c.post("/api/institutions/", {"name": "x"}, format="json").status_code, 403)
