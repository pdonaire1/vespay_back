from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RegisterView,
    ResendOtpView,
    VerifyOtpView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth_login"),
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("verify-otp/", VerifyOtpView.as_view(), name="auth_verify_otp"),
    path("resend-otp/", ResendOtpView.as_view(), name="auth_resend_otp"),
    path("refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth_password_reset_request",
    ),
    path(
        "password-reset/verify/",
        PasswordResetVerifyView.as_view(),
        name="auth_password_reset_verify",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth_password_reset_confirm",
    ),
]