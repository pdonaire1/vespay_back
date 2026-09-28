import hashlib

import pyotp
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import EmailVerification
from apps.security.services import issue_action_token

User = get_user_model()


class DisableTwoFactorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@vespay.com", password="securepassword123")
        self.user.set_totp_secret(pyotp.random_base32())
        self.user.is_2fa_enabled = True
        self.user.save(update_fields=["totp_secret_encrypted", "is_2fa_enabled"])
        self.url = reverse("auth_2fa_disable")
        self.client.force_authenticate(self.user)

    def _disable(self, code=None, action_token=None):
        payload = {}
        if code is not None:
            payload["code"] = code
        if action_token is not None:
            payload["action_token"] = action_token
        return self.client.post(self.url, payload, format="json")

    def test_missing_code_signals_requires_2fa(self):
        response = self._disable()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["requires_2fa"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)

    def test_missing_code_does_not_rate_limit(self):
        for _ in range(6):
            response = self._disable()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_code_is_rejected(self):
        response = self._disable(code="000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["requires_2fa"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)

    def test_valid_totp_disables_2fa(self):
        code = pyotp.TOTP(self.user.totp_secret).now()
        response = self._disable(code=code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertEqual(self.user.totp_secret, "")

    def test_backup_code_disables_2fa(self):
        raw = "abcd-1234"
        self.user.backup_codes = [hashlib.sha256(raw.encode()).hexdigest()]
        self.user.save(update_fields=["backup_codes"])
        response = self._disable(code=raw)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)

    def test_email_code_disables_2fa(self):
        _, code = EmailVerification.issue(self.user, self.user.email)
        response = self._disable(code=code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)

    def test_action_token_disables_2fa(self):
        token = issue_action_token(self.user.pk)
        response = self._disable(action_token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
