from decimal import ROUND_HALF_UP, Decimal

from .models import FeeRule

CENT = Decimal("0.01")


def calculate_fee(amount: Decimal, app_id: str | None = None) -> tuple[Decimal, Decimal]:
    """Devuelve (fee, net_amount) aplicando la regla global o el override por app_id."""
    rule = (
        FeeRule.objects.filter(app_id=app_id, is_active=True).first()
        or FeeRule.objects.filter(app_id__isnull=True, is_active=True).first()
    )
    if rule is None:
        return Decimal("0"), amount.quantize(CENT, rounding=ROUND_HALF_UP)

    fee = amount * rule.percentage / Decimal("100") + rule.fixed_amount
    fee = fee.quantize(CENT, rounding=ROUND_HALF_UP)
    net_amount = (amount - fee).quantize(CENT, rounding=ROUND_HALF_UP)
    return fee, net_amount
