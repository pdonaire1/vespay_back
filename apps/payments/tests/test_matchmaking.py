import pytest

from apps.accounts.models import LinkedAccount
from apps.payments.matchmaking import select_payment_method


@pytest.mark.django_db
def test_uses_recipient_preferred_method_when_sender_has_it(user, other_user):
    LinkedAccount.objects.create(user=user, method="PAYPAL")
    LinkedAccount.objects.create(user=other_user, method="PAYPAL", is_default=True)

    assert select_payment_method(user, other_user) == "PAYPAL"


@pytest.mark.django_db
def test_falls_back_to_most_used_common_method(user, other_user):
    LinkedAccount.objects.create(user=user, method="BINANCE", usage_count=10)
    LinkedAccount.objects.create(user=user, method="PAYPAL", usage_count=1)
    LinkedAccount.objects.create(user=other_user, method="BINANCE")
    LinkedAccount.objects.create(user=other_user, method="PAYPAL")

    assert select_payment_method(user, other_user) == "BINANCE"


@pytest.mark.django_db
def test_returns_none_without_overlap(user, other_user):
    LinkedAccount.objects.create(user=user, method="PAYPAL")
    LinkedAccount.objects.create(user=other_user, method="BINANCE")

    assert select_payment_method(user, other_user) is None
