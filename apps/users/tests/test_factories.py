import pytest


@pytest.mark.django_db
def test_user_factory_creates_valid_user(user):
    assert user.pk is not None
    assert user.email.endswith("@example.com")
    assert user.check_password("supersecret-pass-123")
    assert not user.is_staff


@pytest.mark.django_db
def test_superuser_factory(superuser):
    assert superuser.is_staff
    assert superuser.is_superuser
    assert superuser.check_password("supersecret-pass-123")
