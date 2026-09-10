from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ChangePasswordViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@vespay.com", password="oldpassword123"
        )
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