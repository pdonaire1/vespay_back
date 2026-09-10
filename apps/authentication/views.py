from datetime import timedelta

import hashlib
import secrets

import pyotp
import requests as http_requests
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import UserSerializer

from .models import RESEND_THROTTLE_SECONDS, EmailVerification
from .serializers import RegisterSerializer

User = get_user_model()

PASSWORD_RESET_TOKEN_MAX_AGE = 60 * 15  # segundos
PASSWORD_RESET_TOKEN_SALT = "vespay.password.reset"
PRE_AUTH_TOKEN_MAX_AGE = 60 * 5  # segundos
PRE_AUTH_TOKEN_SALT = "vespay.2fa.pre_auth"
TWO_FA_MAX_ATTEMPTS = 5
TWO_FA_ATTEMPT_WINDOW = 60 * 15  # segundos


def _new_backup_codes(count: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(count)]


def _dispatch_otp_email(email: str, code: str) -> None:
    context = {"otp_code": code, "email": email}
    subject = "Tu código de verificación VesPay"
    text_message = render_to_string("emails/otp_code.txt", context)
    html_message = render_to_string("emails/otp_code.html", context)
    send_mail(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )


def _dispatch_password_reset_email(email: str, code: str) -> None:
    reset_link = (
        f"{settings.FRONTEND_URL.rstrip('/')}/#/auth/verify-otp"
        f"?email={email}&mode=reset&code={code}"
    )
    context = {"otp_code": code, "email": email, "reset_link": reset_link}
    subject = "Restablece tu contraseña VesPay"
    text_message = render_to_string("emails/password_reset_code.txt", context)
    html_message = render_to_string("emails/password_reset_code.html", context)
    send_mail(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )


def _send_otp_code(user) -> bool:
    """Issues and emails a fresh verification code unless a recent one is pending.

    Returns True if a new code was dispatched, False when throttled.
    """
    latest = (
        EmailVerification.objects.filter(user=user, is_used=False).order_by("-id").first()
    )
    if latest and latest.created_at > timezone.now() - timedelta(
        seconds=RESEND_THROTTLE_SECONDS
    ):
        return False

    _, code = EmailVerification.issue(user, user.email)
    _dispatch_otp_email(user.email, code)
    return True


def _send_password_reset_code(user) -> None:
    """Dispatches a fresh reset code. Always sends: this is an explicit,
    user-initiated action, so it must not be silently throttled by other OTP
    traffic (register/login/resend share the same storage)."""
    _, code = EmailVerification.issue(user, user.email)
    _dispatch_password_reset_email(user.email, code)


def _verify_access_token(token: str) -> dict | None:
    """Validates a Google OAuth2 access token via the tokeninfo endpoint.

    Used for web clients, where google_sign_in does not expose an id_token.
    """
    try:
        response = http_requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": token},
            timeout=10,
        )
    except http_requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return response.json()


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))

        user = authenticate(request=request, email=email, password=password)
        if user is None:
            return Response(
                {"detail": "Wrong password or user does not exist"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_email_verified:
            _send_otp_code(user)

        if user.is_2fa_enabled:
            pre_auth_token = signing.dumps(
                {"user_id": user.pk}, salt=PRE_AUTH_TOKEN_SALT
            )
            return Response(
                {"requires_2fa": True, "pre_auth_token": pre_auth_token},
                status=status.HTTP_202_ACCEPTED,
            )

        first_login = user.last_login is None
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "first_login": first_login,
            },
            status=status.HTTP_200_OK,
        )


class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        id_token_str = str(request.data.get("id_token", "")).strip()
        access_token = str(request.data.get("access_token", "")).strip()
        invalid = Response(
            {"detail": "Invalid Google ID Token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

        payload = None
        if id_token_str:
            try:
                payload = id_token.verify_oauth2_token(
                    id_token_str,
                    google_requests.Request(),
                    settings.GOOGLE_WEB_CLIENT_ID,
                )
            except (ValueError, GoogleAuthError):
                return invalid
        elif access_token:
            payload = _verify_access_token(access_token)
            if payload is None:
                return invalid
        if payload is None:
            return invalid

        email = str(payload.get("email") or "").strip().lower()
        if not email:
            return invalid

        full_name = " ".join(
            part
            for part in (
                str(payload.get("given_name") or "").strip(),
                str(payload.get("family_name") or "").strip(),
            )
            if part
        )
        if not full_name:
            full_name = str(payload.get("name") or "").strip()

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "is_email_verified": True,
                "password": make_password(None),  # cuenta SSO sin contraseña
            },
        )
        first_login = user.last_login is None

        # Cuentas legacy creadas por SSO pueden tener password="" (que Django
        # considera "usable"). Normaliza a unusable; una contraseña real
        # (p.ej. asignada vía forgot-password) se conserva.
        if not user.password or not user.has_usable_password():
            user.set_unusable_password()
            user.save(update_fields=["password"])

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        if user.is_2fa_enabled:
            pre_auth_token = signing.dumps(
                {"user_id": user.pk}, salt=PRE_AUTH_TOKEN_SALT
            )
            return Response(
                {"requires_2fa": True, "pre_auth_token": pre_auth_token},
                status=status.HTTP_202_ACCEPTED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "first_login": first_login,
            },
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        _, code = EmailVerification.issue(user, user.email)
        _dispatch_otp_email(user.email, code)

        return Response(
            {
                "id": user.pk,
                "email": user.email,
                "is_email_verified": user.is_email_verified,
            },
            status=status.HTTP_201_CREATED,
        )


class ResendOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        bad_request = Response(
            {"detail": "Invalid or expired OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        if not email:
            return bad_request

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return bad_request

        if user.is_email_verified:
            return Response(
                {"detail": "Email already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _send_otp_code(user):
            return Response(
                {"detail": "Please wait before requesting another code."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return Response(
            {"detail": "A new verification code has been sent to your email."},
            status=status.HTTP_200_OK,
        )


class VerifyOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        otp_code = str(request.data.get("otp_code", "")).strip()
        invalid = Response(
            {"detail": "Invalid or expired OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        if not otp_code or not email:
            return invalid

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return invalid

        verification = (
            EmailVerification.objects.filter(user=user, is_used=False).order_by("-id").first()
        )
        if (
            verification is None
            or verification.is_expired
            or not verification.matches(otp_code)
        ):
            return invalid

        verification.is_used = True
        verification.save(update_fields=["is_used"])

        first_login = user.last_login is None
        user.is_email_verified = True
        user.last_login = timezone.now()
        user.save(update_fields=["is_email_verified", "last_login"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "detail": "Email verified successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "first_login": first_login,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """Changes the password of the currently authenticated user."""

    def post(self, request):
        current_password = str(request.data.get("current_password", ""))
        new_password = str(request.data.get("new_password", ""))

        if not request.user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=request.user)
        except ValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class TwoFactorSetupView(APIView):
    """Genera el secreto TOTP y su URI de aprovisionamiento (se muestra 1 vez)."""

    def post(self, request):
        if request.user.is_2fa_enabled:
            return Response({"message": "2FA ya está activado."}, status=400)
        secret = pyotp.random_base32()
        request.user.totp_secret = secret
        request.user.save(update_fields=["totp_secret"])
        qr_uri = pyotp.TOTP(secret).provisioning_uri(
            name=request.user.email,
            issuer_name="VesPay",
        )
        return Response({"secret": secret, "qr_uri": qr_uri}, status=200)


class TwoFactorVerifyView(APIView):
    """Valida el primer código; solo entonces se activa el 2FA."""

    def post(self, request):
        code = str(request.data.get("code", "")).strip()
        user = request.user
        if user.is_2fa_enabled:
            return Response({"message": "2FA ya está activado."}, status=400)
        if not user.totp_secret:
            return Response(
                {"message": "Debes generar el código QR primero."}, status=400
            )
        if not code or not pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            return Response({"message": "Código inválido."}, status=400)

        codes = _new_backup_codes()
        user.backup_codes = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
        user.is_2fa_enabled = True
        user.save(update_fields=["backup_codes", "is_2fa_enabled"])
        return Response(
            {"message": "2FA activado correctamente", "backup_codes": codes}, status=200
        )


class TwoFactorChallengeView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        token = str(request.data.get("pre_auth_token", "")).strip()
        code = str(request.data.get("code", "")).strip()
        invalid = Response(
            {"detail": "Código inválido o expirado."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        user = None
        if token:
            try:
                payload = signing.loads(
                    token,
                    salt=PRE_AUTH_TOKEN_SALT,
                    max_age=PRE_AUTH_TOKEN_MAX_AGE,
                )
                uid = payload.get("user_id")
                if isinstance(uid, int):
                    user = User.objects.filter(id=uid).first()
            except (signing.BadSignature, signing.SignatureExpired):
                user = None
        if user is None:
            return invalid

        cache_key = f"2fa_challenge_failures:{user.pk}"
        failures = cache.get(cache_key, 0)
        if failures >= TWO_FA_MAX_ATTEMPTS:
            return Response(
                {"detail": "Demasiados intentos. Intenta nuevamente en 15 minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        valid = False
        if user.totp_secret and code:
            valid = pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)
        if not valid and code:
            valid = _consume_backup_code(user, code)

        if not valid:
            cache.set(cache_key, failures + 1, timeout=TWO_FA_ATTEMPT_WINDOW)
            return invalid

        cache.delete(cache_key)
        first_login = user.last_login is None
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "first_login": first_login,
            },
            status=status.HTTP_200_OK,
        )


def _consume_backup_code(user, code: str) -> bool:
    code_hash = hashlib.sha256(code.strip().encode()).hexdigest()
    codes = user.backup_codes or []
    if code_hash not in codes:
        return False
    user.backup_codes = [c for c in codes if c != code_hash]
    user.save(update_fields=["backup_codes"])
    return True


class TwoFactorDisableView(APIView):
    def post(self, request):
        user = request.user
        user.totp_secret = ""
        user.is_2fa_enabled = False
        user.backup_codes = []
        user.save(update_fields=["totp_secret", "is_2fa_enabled", "backup_codes"])
        return Response({"message": "2FA desactivado."}, status=200)


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        # Respuesta idéntica haya o no cuenta (evita enumeración de usuarios).
        if email:
            user = User.objects.filter(email=email).first()
            if user is not None:
                _send_password_reset_code(user)
        return Response({"detail": "Reset code sent."}, status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        code = str(request.data.get("code", "")).strip()
        invalid = Response(
            {"detail": "Invalid or expired OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        if not email or not code:
            return invalid

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return invalid

        verification = (
            EmailVerification.objects.filter(user=user, is_used=False).order_by("-id").first()
        )
        if (
            verification is None
            or verification.is_expired
            or not verification.matches(code)
        ):
            return invalid

        verification.is_used = True
        verification.save(update_fields=["is_used"])

        reset_token = signing.dumps({"user_id": user.pk}, salt=PASSWORD_RESET_TOKEN_SALT)
        return Response({"reset_token": reset_token}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        reset_token = str(request.data.get("reset_token", "")).strip()
        new_password = str(request.data.get("new_password", ""))
        invalid = Response(
            {"detail": "Invalid or expired reset token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        user = None
        if reset_token:
            try:
                payload = signing.loads(
                    reset_token,
                    salt=PASSWORD_RESET_TOKEN_SALT,
                    max_age=PASSWORD_RESET_TOKEN_MAX_AGE,
                )
                user_id = payload.get("user_id")
                if isinstance(user_id, int):
                    user = User.objects.filter(id=user_id).first()
            except (signing.BadSignature, signing.SignatureExpired):
                user = None

        if user is None:
            return invalid

        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.is_email_verified = True
        user.save(update_fields=["password", "is_email_verified"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "detail": "Password updated successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )