import pytest

from apps.users.tests.factories import SuperUserFactory, UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def superuser(db):
    return SuperUserFactory()
