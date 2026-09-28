import secrets

from django.core.cache import cache

REG_CHALLENGE_TTL = 300  # segundos
AUTH_CHALLENGE_TTL = 60  # segundos
ACTION_TOKEN_TTL = 300  # segundos


def reg_challenge_key(user_id: int) -> str:
    return f"webauthn_reg_challenge:{user_id}"


def auth_challenge_key(user_id: int) -> str:
    return f"webauthn_auth_challenge:{user_id}"


def action_token_key(user_id: int, token: str) -> str:
    return f"biometric_action_token:{user_id}:{token}"


def issue_action_token(user_id: int) -> str:
    """Emite un token de acción de corta vida tras una verificación biométrica."""
    token = secrets.token_urlsafe(32)
    cache.set(action_token_key(user_id, token), True, ACTION_TOKEN_TTL)
    return token


def consume_action_token(user, token: str) -> bool:
    """Valida y consume (single-use) un action_token biométrico."""
    if not token:
        return False
    key = action_token_key(user.pk, token)
    if cache.get(key):
        cache.delete(key)
        return True
    return False
