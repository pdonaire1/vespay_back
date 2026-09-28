import hashlib

import pyotp
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import EmailVerification
from apps.security.services import issue_action_token

User = get_user_model()


class ChangePasswordViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@vespay.com", password="oldpassword123")
        self.url = reverse("auth_change_password")

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(
            self.url,
            {"current_password": "x", "new_password": "newpassword123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_current_password_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url,
            {"current_password": "wrongpass", "new_password": "newpassword123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Current password is incorrect.")

    def test_weak_new_password_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url,
            {"current_password": "oldpassword123", "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_valid_change_updates_password(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url,
            {"current_password": "oldpassword123", "new_password": "newpassword123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))
        self.assertFalse(self.user.check_password("oldpassword123"))


class ChangePasswordTwoFactorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@vespay.com", password="oldpassword123")
        self.user.set_totp_secret(pyotp.random_base32())
        self.user.is_2fa_enabled = True
        self.user.save(update_fields=["totp_secret_encrypted", "is_2fa_enabled"])
        self.url = reverse("auth_change_password")
        self.client.force_authenticate(self.user)

    def _change(self, new_password="newpassword123", code=None):
        payload = {
            "current_password": "oldpassword123",
            "new_password": new_password,
        }
        if code is not None:
            payload["code"] = code
        return self.client.post(self.url, payload, format="json")

    def test_missing_code_signals_requires_2fa(self):
        response = self._change()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["requires_2fa"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpassword123"))

    def test_missing_code_does_not_rate_limit(self):
        # Un intento sin código no debe contar como fallo (el cliente solo sondea).
        for _ in range(6):
            response = self._change()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("requires_2fa") is None)

    def test_invalid_code_is_rejected(self):
        response = self._change(code="000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["requires_2fa"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpassword123"))

    def test_valid_totp_code_changes_password(self):
        code = pyotp.TOTP(self.user.totp_secret).now()
        response = self._change(code=code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_backup_code_changes_password(self):
        raw = "abcd-1234"
        self.user.backup_codes = [hashlib.sha256(raw.encode()).hexdigest()]
        self.user.save(update_fields=["backup_codes"])
        response = self._change(code=raw)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_email_code_is_not_accepted_for_change_password(self):
        _, code = EmailVerification.issue(self.user, self.user.email)
        response = self._change(code=code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpassword123"))

    def test_rate_limit_after_5_failures(self):
        for _ in range(5):
            self._change(code="000000")
        response = self._change(code="000000")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_valid_action_token_changes_password_without_code(self):
        token = issue_action_token(self.user.pk)
        response = self.client.post(
            self.url,
            {
                "current_password": "oldpassword123",
                "new_password": "newpassword123",
                "action_token": token,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_action_token_is_single_use(self):
        token = issue_action_token(self.user.pk)
        payload = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "action_token": token,
        }
        first = self.client.post(self.url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.url,
            {
                "current_password": "newpassword123",
                "new_password": "anotherpassword123",
                "action_token": token,
            },
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_action_token_falls_back_to_code(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "oldpassword123",
                "new_password": "newpassword123",
                "action_token": "garbage",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpassword123"))
