from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class CurrentUserViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@vespay.com", password="securepassword123")
        self.url = reverse("auth_me")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_security_flags(self):
        self.user.is_2fa_enabled = True
        self.user.set_totp_secret("JBSWY3DPEHPK3PXP")
        self.user.save(update_fields=["is_2fa_enabled", "totp_secret_encrypted"])

        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@vespay.com")
        self.assertTrue(response.data["is_2fa_enabled"])
        self.assertTrue(response.data["has_usable_password"])
