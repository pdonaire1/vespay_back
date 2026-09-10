from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class PasswordUserFlagTests(APITestCase):
    def test_register_and_login_expose_usable_password(self):
        register = self.client.post(
            reverse("auth_register"),
            {"email": "user@vespay.com", "password": "securepassword123"},
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email="user@vespay.com")
        self.assertTrue(user.has_usable_password())

        login = self.client.post(
            reverse("auth_login"),
            {"email": "user@vespay.com", "password": "securepassword123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(login.data["user"]["has_usable_password"])