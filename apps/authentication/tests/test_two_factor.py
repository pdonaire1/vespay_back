import pyotp
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TwoFactorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@vespay.com", password="securepassword123"
        )
        self.client.force_authenticate(self.user)

    def _enable_2fa(self) -> list[str]:
        setup = self.client.post(reverse("auth_2fa_setup"), {}, format="json")
        assert setup.status_code == 200
        secret = setup.data["secret"]
        code = pyotp.TOTP(secret).now()
        verify = self.client.post(
            reverse("auth_2fa_verify"), {"code": code}, format="json"
        )
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
        return verify.data["backup_codes"]

    def _login_after_2fa(self):
        return self.client.post(
            reverse("auth_login"),
            {"email": self.user.email, "password": "securepassword123"},
            format="json",
        )

    def test_setup_returns_secret_and_uri(self):
        response = self.client.post(reverse("auth_2fa_setup"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret", response.data)
        self.assertIn("otpauth://totp/VesPay:", response.data["qr_uri"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)

    def test_verify_activates_and_returns_backup_codes(self):
        backup = self._enable_2fa()
        self.assertEqual(len(backup), 8)

    def test_secret_not_exposed_after_activation(self):
        self._enable_2fa()
        response = self._login_after_2fa()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        # El secreto nunca viaja en el payload del usuario.
        self.assertNotIn("totp_secret", str(response.data))

    def test_verify_activates_then_login_requires_2fa(self):
        self._enable_2fa()
        response = self._login_after_2fa()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["requires_2fa"])
        self.assertNotIn("access", response.data)
        self.assertIn("pre_auth_token", response.data)

    def test_challenge_with_valid_totp_returns_tokens(self):
        self._enable_2fa()
        token = self._login_after_2fa().data["pre_auth_token"]
        code = pyotp.TOTP(self.user.totp_secret).now()
        response = self.client.post(
            reverse("auth_2fa_challenge"),
            {"pre_auth_token": token, "code": code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_challenge_with_invalid_code_is_rejected(self):
        self._enable_2fa()
        token = self._login_after_2fa().data["pre_auth_token"]
        response = self.client.post(
            reverse("auth_2fa_challenge"),
            {"pre_auth_token": token, "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_backup_code_works_once(self):
        backups = self._enable_2fa()
        token = self._login_after_2fa().data["pre_auth_token"]
        code = backups[0]
        ok = self.client.post(
            reverse("auth_2fa_challenge"),
            {"pre_auth_token": token, "code": code},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(None)
        token2 = self._login_after_2fa().data["pre_auth_token"]
        reused = self.client.post(
            reverse("auth_2fa_challenge"),
            {"pre_auth_token": token2, "code": code},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rate_limit_after_5_failures(self):
        self._enable_2fa()
        token = self._login_after_2fa().data["pre_auth_token"]
        for _ in range(5):
            self.client.post(
                reverse("auth_2fa_challenge"),
                {"pre_auth_token": token, "code": "000000"},
                format="json",
            )
        response = self.client.post(
            reverse("auth_2fa_challenge"),
            {"pre_auth_token": token, "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)