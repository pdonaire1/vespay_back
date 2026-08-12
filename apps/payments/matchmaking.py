from apps.accounts.models import LinkedAccount


def select_payment_method(sender, recipient) -> str | None:
    """Resuelve el método de pago entre emisor y receptor.

    1. Método preferido (is_default) del receptor si el emisor lo tiene activo.
    2. Cruce de plataformas comunes ordenado por frecuencia de uso.
    3. Sin cruce -> devuelve None (la app solicita selección manual).
    """
    sender_methods = set(
        LinkedAccount.objects.filter(user=sender, is_active=True).values_list("method", flat=True)
    )
    recipient_methods = set(
        LinkedAccount.objects.filter(user=recipient, is_active=True).values_list(
            "method", flat=True
        )
    )

    preferred = (
        LinkedAccount.objects.filter(user=recipient, is_default=True, is_active=True)
        .values_list("method", flat=True)
        .first()
    )
    if preferred in sender_methods:
        return preferred

    common = sender_methods & recipient_methods
    if common:
        return (
            LinkedAccount.objects.filter(user=sender, method__in=common)
            .order_by("-usage_count")
            .values_list("method", flat=True)
            .first()
        )

    return None
