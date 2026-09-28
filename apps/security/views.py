import json

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.parse_authentication_credential_json import (
    parse_authentication_credential_json,
)
from webauthn.helpers.parse_registration_credential_json import (
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import UserBiometricCredential
from .services import (
    AUTH_CHALLENGE_TTL,
    REG_CHALLENGE_TTL,
    auth_challenge_key,
    issue_action_token,
    reg_challenge_key,
)


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


class BiometricRegisterOptionsView(APIView):
    """Genera las opciones de registro de un passkey para el usuario autenticado."""

    def post(self, request):
        user = request.user
        existing = list(
            UserBiometricCredential.objects.filter(user=user).values_list(
                "credential_id", flat=True
            )
        )
        options = generate_registration_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=str(user.pk).encode(),
            user_name=user.email,
            user_display_name=user.get_full_name(),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid)) for cid in existing
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        cache.set(
            reg_challenge_key(user.pk),
            bytes_to_base64url(options.challenge),
            REG_CHALLENGE_TTL,
        )
        return Response(json.loads(options_to_json(options)), status=status.HTTP_200_OK)


class BiometricRegisterVerifyView(APIView):
    """Valida la attestation del passkey y guarda la clave pública."""

    def post(self, request):
        user = request.user
        challenge_b64 = cache.get(reg_challenge_key(user.pk))
        if not challenge_b64:
            return _bad_request("El registro expiró. Intenta nuevamente.")

        try:
            credential = parse_registration_credential_json(request.data)
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(challenge_b64),
                expected_origin=settings.WEBAUTHN_ORIGIN,
                expected_rp_id=settings.WEBAUTHN_RP_ID,
            )
        except (InvalidRegistrationResponse, ValueError, KeyError, TypeError):
            return _bad_request("Registro biométrico inválido.")

        cache.delete(reg_challenge_key(user.pk))

        credential_id = bytes_to_base64url(verification.credential_id)
        UserBiometricCredential.objects.update_or_create(
            credential_id=credential_id,
            defaults={
                "user": user,
                "public_key": bytes_to_base64url(verification.credential_public_key),
                "sign_count": verification.sign_count,
                "transports": list(getattr(credential, "transports", []) or []),
                "device_name": str(request.data.get("device_name", ""))[:100],
            },
        )
        return Response({"verified": True}, status=status.HTTP_200_OK)


class BiometricChallengeView(APIView):
    """Emite un challenge de autenticación (nonce) para firmar con el passkey."""

    def post(self, request):
        user = request.user
        credentials = list(UserBiometricCredential.objects.filter(user=user))
        if not credentials:
            return _bad_request("No hay una credencial biométrica registrada.")

        options = generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
                for c in credentials
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        cache.set(
            auth_challenge_key(user.pk),
            bytes_to_base64url(options.challenge),
            AUTH_CHALLENGE_TTL,
        )
        return Response(
            {
                **json.loads(options_to_json(options)),
                "rpId": settings.WEBAUTHN_RP_ID,
                "timeout": AUTH_CHALLENGE_TTL * 1000,
            },
            status=status.HTTP_200_OK,
        )


class BiometricVerifyView(APIView):
    """Valida la firma del passkey y emite un action_token de corta vida."""

    def post(self, request):
        user = request.user
        challenge_b64 = cache.get(auth_challenge_key(user.pk))
        if not challenge_b64:
            return _bad_request("El challenge expiró. Intenta nuevamente.")

        try:
            credential = parse_authentication_credential_json(request.data)
        except (ValueError, KeyError, TypeError):
            return _bad_request("Aserción biométrica inválida.")

        raw_id = credential.id
        credential_id = raw_id if isinstance(raw_id, str) else bytes_to_base64url(raw_id)
        stored = UserBiometricCredential.objects.filter(
            user=user, credential_id=credential_id
        ).first()
        if stored is None:
            return _bad_request("Credencial biométrica no reconocida.")

        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(challenge_b64),
                expected_origin=settings.WEBAUTHN_ORIGIN,
                expected_rp_id=settings.WEBAUTHN_RP_ID,
                credential_public_key=base64url_to_bytes(stored.public_key),
                credential_current_sign_count=stored.sign_count,
            )
        except (InvalidAuthenticationResponse, ValueError, KeyError, TypeError):
            return _bad_request("Verificación biométrica fallida.")

        # Consumo del challenge: garantía de unicidad (anti-replay).
        cache.delete(auth_challenge_key(user.pk))

        stored.sign_count = max(stored.sign_count, verification.new_sign_count)
        stored.last_used_at = timezone.now()
        stored.save(update_fields=["sign_count", "last_used_at", "updated_at"])

        token = issue_action_token(user.pk)
        return Response({"verified": True, "action_token": token}, status=status.HTTP_200_OK)
