from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from kombu.exceptions import OperationalError
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

VERIFICATION_TASK = "apps.authentication.tasks.send_verification_otp_email.delay"
RESET_TASK = "apps.authentication.tasks.send_password_reset_email.delay"


class EmailTaskDispatchTests(APITestCase):
    def test_register_enqueues_verification_email(self):
        with mock.patch(VERIFICATION_TASK) as delay:
            response = self.client.post(
                reverse("auth_register"),
                {"email": "new@vespay.com", "password": "securepassword123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(delay.call_count, 1)
        email_arg, code_arg = delay.call_args.args
        self.assertEqual(email_arg, "new@vespay.com")
        self.assertEqual(len(code_arg), 6)

    def test_register_runs_email_task_eagerly_without_broker(self):
        response = self.client.post(
            reverse("auth_register"),
            {"email": "new@vespay.com", "password": "securepassword123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@vespay.com"])

    def test_register_succeeds_when_broker_unavailable(self):
        with mock.patch(VERIFICATION_TASK, side_effect=OperationalError("broker down")):
            response = self.client.post(
                reverse("auth_register"),
                {"email": "new@vespay.com", "password": "securepassword123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_password_reset_request_enqueues_email(self):
        User.objects.create_user(email="user@vespay.com", password="securepassword123")

        with mock.patch(RESET_TASK) as delay:
            response = self.client.post(
                reverse("auth_password_reset_request"),
                {"email": "user@vespay.com"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(delay.call_count, 1)
        email_arg, code_arg = delay.call_args.args
        self.assertEqual(email_arg, "user@vespay.com")
        self.assertEqual(len(code_arg), 6)

    def test_unverified_login_enqueues_verification_email(self):
        User.objects.create_user(email="user@vespay.com", password="securepassword123")

        with mock.patch(VERIFICATION_TASK) as delay:
            response = self.client.post(
                reverse("auth_login"),
                {"email": "user@vespay.com", "password": "securepassword123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["user"]["is_email_verified"])
        self.assertEqual(delay.call_count, 1)
        email_arg, code_arg = delay.call_args.args
        self.assertEqual(email_arg, "user@vespay.com")
        self.assertEqual(len(code_arg), 6)
