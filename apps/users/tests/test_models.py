import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_create_user_normalizes_email():
    user = get_user_model().objects.create_user(email="User@Example.com", password="secret1234")

    assert user.email == "User@example.com"
    assert user.check_password("secret1234")
    assert not user.is_staff


@pytest.mark.django_db
def test_create_superuser():
    user = get_user_model().objects.create_superuser(
        email="admin@example.com", password="secret1234"
    )

    assert user.is_staff
    assert user.is_superuser
