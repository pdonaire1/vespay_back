from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
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

        refresh = RefreshToken.for_user(user)
        if not user.is_email_verified:
            _send_otp_code(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
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

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "detail": "Email verified successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


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