from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import RM, RMLoginHistory
from easypay.models import RMPayment, RMGPayPayment


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

    def test_all_transactions_lists_payments_for_logged_in_rm(self):
        RMLoginHistory.objects.create(
            rm=self.rm,
            login_time=timezone.now(),
            status=True,
            last_heartbeat=timezone.now(),
        )
        self.client.session["rm_id"] = self.rm.id
        self.client.session["rm_code"] = self.rm.rm_code
        self.client.session.save()

        RMPayment.objects.create(
            rm_code=self.rm.rm_code,
            rm_name=self.rm.rm_name,
            donor_name="Donor One",
            donor_email="donor@example.com",
            donor_mobile="9999999999",
            donor_amount="100.00",
            txnid="txn-test-1",
            submitted_at=timezone.now(),
        )
        RMGPayPayment.objects.create(
            rm=self.rm,
            rm_code=self.rm.rm_code,
            rm_name=self.rm.rm_name,
            rm_email=self.rm.rm_email,
            donor_name="Donor Two",
            donor_email="donor2@example.com",
            donor_mobile="8888888888",
            amount="200.00",
            payment_date=timezone.now(),
            gpay_reference_id="gpay-test-1",
        )

        response = self.client.get(reverse("all_transaction"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["transactions"]), 2)
