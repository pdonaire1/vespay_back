from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.security.models import UserBiometricCredential
from apps.security.services import auth_challenge_key, reg_challenge_key

User = get_user_model()


class BiometricEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@vespay.com", password="securepassword123")

    def test_register_options_requires_authentication(self):
        response = self.client.post(reverse("biometric_register"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_options_returns_challenge_and_stores_it(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("biometric_register"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("challenge", response.data)
        self.assertEqual(response.data["rp"]["id"], "localhost")
        self.assertIsNotNone(cache.get(reg_challenge_key(self.user.pk)))

    def test_register_verify_without_challenge_is_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("biometric_register_verify"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_challenge_without_registered_credential_is_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("biometric_challenge"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_challenge_returns_allow_credentials_and_stores_it(self):
        UserBiometricCredential.objects.create(
            user=self.user,
            credential_id="dGVzdC1jcmVk",
            public_key="cHVibGljLWtleQ",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("biometric_challenge"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("challenge", response.data)
        self.assertEqual(len(response.data["allowCredentials"]), 1)
        self.assertIsNotNone(cache.get(auth_challenge_key(self.user.pk)))

    def test_verify_without_challenge_is_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("biometric_verify"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
