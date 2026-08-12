import hashlib
import hmac
import secrets

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from .models import PayeeToken, PayerToken

_PAYER_PREFIX = "vsp_ptk"
_PAYEE_PREFIX = "vsp_ytk"


def _sign(payload: str) -> str:
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_token(prefix: str) -> str:
    payload = f"{prefix}_{secrets.token_hex(16)}"
    return f"{payload}.{_sign(payload)}"


def validate_token_signature(token: str, prefix: str) -> bool:
    try:
        payload, signature = token.rsplit(".", 1)
    except ValueError:
        return False
    if not payload.startswith(f"{prefix}_"):
        return False
    return hmac.compare_digest(_sign(payload), signature)


def create_payer_token(user) -> PayerToken:
    return PayerToken.objects.create(user=user, token=generate_token(_PAYER_PREFIX))


def create_payee_token(user, amount, currency) -> PayeeToken:
    return PayeeToken.objects.create(
        user=user,
        token=generate_token(_PAYEE_PREFIX),
        amount=amount,
        currency=currency,
    )


def notify_session(session_id: str, event: str, payload: dict) -> None:
    """Envía un evento al grupo WebSocket de la sesión NFC (< 500 ms requerido)."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"nfc_{session_id}",
        {"type": "payment.event", "event": event, "payload": payload},
    )
