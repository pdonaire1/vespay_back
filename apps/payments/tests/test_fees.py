from decimal import Decimal

import pytest

from apps.payments.fees import calculate_fee
from apps.payments.models import FeeRule


@pytest.mark.django_db
def test_calculate_fee_global_rule():
    FeeRule.objects.create(percentage=Decimal("1.2"), fixed_amount=Decimal("0.20"))

    fee, net = calculate_fee(Decimal("100.00"))

    assert fee == Decimal("1.40")
    assert net == Decimal("98.60")


@pytest.mark.django_db
def test_calculate_fee_app_override():
    FeeRule.objects.create(percentage=Decimal("1.2"), fixed_amount=Decimal("0.20"))
    FeeRule.objects.create(app_id="app_x", percentage=Decimal("0.5"), fixed_amount=Decimal("0"))

    fee, net = calculate_fee(Decimal("100.00"), app_id="app_x")

    assert fee == Decimal("0.50")
    assert net == Decimal("99.50")


@pytest.mark.django_db
def test_calculate_fee_without_rules():
    fee, net = calculate_fee(Decimal("50.00"))

    assert fee == Decimal("0")
    assert net == Decimal("50.00")
