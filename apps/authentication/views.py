from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
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


def _send_otp_code(user) -> bool:
    """Issues and emails a fresh code unless a recent pending one still exists.

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