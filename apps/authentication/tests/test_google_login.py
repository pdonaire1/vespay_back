from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from google.auth.exceptions import GoogleAuthError
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


def _fake_payload(**overrides):
    payload = {
        "sub": "1234567890",
        "email": "ana.gomez@gmail.com",
        "given_name": "Ana",
        "family_name": "Gomez",
    }
    payload.update(overrides)
    return payload


class GoogleLoginViewTests(APITestCase):
    def test_creates_user_and_returns_tokens(self):
        with mock.patch(
            "apps.authentication.views.id_token.verify_oauth2_token",
            return_value=_fake_payload(),
        ):
            response = self.client.post(
                reverse("google_login"),
                {"id_token": "valid-token"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "ana.gomez@gmail.com")
        user = User.objects.get(email="ana.gomez@gmail.com")
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.full_name, "Ana Gomez")

    def test_existing_user_is_reused_and_verified(self):
        User.objects.create_user(email="ana.gomez@gmail.com", password="sometestpass")
        with mock.patch(
            "apps.authentication.views.id_token.verify_oauth2_token",
            return_value=_fake_payload(),
        ):
            response = self.client.post(
                reverse("google_login"),
                {"id_token": "valid-token"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.filter(email="ana.gomez@gmail.com").count(), 1)

    def test_invalid_token_returns_400(self):
        for exc in (ValueError("bad"), GoogleAuthError("bad")):
            with self.subTest(exc=type(exc).__name__):
                with mock.patch(
                    "apps.authentication.views.id_token.verify_oauth2_token",
                    side_effect=exc,
                ):
                    response = self.client.post(
                        reverse("google_login"),
                        {"id_token": "invalid"},
                        format="json",
                    )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["detail"], "Invalid Google ID Token")

    def test_missing_token_returns_400(self):
        response = self.client.post(reverse("google_login"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_token_flow_creates_user(self):
        fake_info = {
            "sub": "123",
            "email": "ana.gomez@gmail.com",
            "email_verified": "true",
            "aud": "web-client-id",
        }
        with mock.patch(
            "apps.authentication.views.http_requests.get",
            return_value=mock.Mock(status_code=200, json=lambda: fake_info),
        ):
            response = self.client.post(
                reverse("google_login"),
                {"access_token": "access-token"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], "ana.gomez@gmail.com")
        user = User.objects.get(email="ana.gomez@gmail.com")
        self.assertTrue(user.is_email_verified)

    def test_invalid_access_token_returns_400(self):
        for status_code in (400, 401, 500):
            with self.subTest(status_code=status_code):
                with mock.patch(
                    "apps.authentication.views.http_requests.get",
                    return_value=mock.Mock(status_code=status_code, json=lambda: {}),
                ):
                    response = self.client.post(
                        reverse("google_login"),
                        {"access_token": "bad"},
                        format="json",
                    )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)