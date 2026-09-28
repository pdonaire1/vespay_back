import pytest
from django.core.cache import cache

from apps.users.tests.factories import SuperUserFactory, UserFactory


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Limpia la caché entre tests (throttles y contadores de 2FA)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def superuser(db):
    return SuperUserFactory()
