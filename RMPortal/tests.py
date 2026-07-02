from django.test import TestCase
from django.urls import reverse

from dashboard.models import RM


class RMPortalAuthTests(TestCase):
    def setUp(self):
        self.rm = RM.objects.create(
            rm_name="Alice",
            rm_email="alice@example.com",
            rm_password="secret123",
            rm_code="AL01",
            is_active=True,
        )
        self.other_rm = RM.objects.create(
            rm_name="Bob",
            rm_email="bob@example.com",
            rm_password="password456",
            rm_code="BO02",
            is_active=True,
        )

    def test_login_accepts_registered_rm_credentials(self):
        response = self.client.post(
            reverse("rm_login"),
            {"username": self.rm.rm_email, "password": "secret123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("webchat", kwargs={"rm_code": self.rm.rm_code}))
        self.assertEqual(self.client.session["rm_id"], self.rm.id)

    def test_invalid_login_does_not_grant_portal_access(self):
        self.client.post(
            reverse("rm_login"),
            {"username": self.rm.rm_email, "password": "wrong-password"},
        )

        response = self.client.get(reverse("rmportal_index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("rm_login"))

    def test_rm_cannot_access_another_rms_dashboard(self):
        self.client.post(
            reverse("rm_login"),
            {"username": self.rm.rm_email, "password": "secret123"},
        )

        response = self.client.get(reverse("webchat", kwargs={"rm_code": self.other_rm.rm_code}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("webchat", kwargs={"rm_code": self.rm.rm_code}))
