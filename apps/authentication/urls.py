from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    GoogleLoginView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RegisterView,
    ResendOtpView,
    TwoFactorChallengeView,
    TwoFactorDisableView,
    TwoFactorSetupView,
    TwoFactorVerifyView,
    VerifyOtpView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth_login"),
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
    path("verify-otp/", VerifyOtpView.as_view(), name="auth_verify_otp"),
    path("resend-otp/", ResendOtpView.as_view(), name="auth_resend_otp"),
    path("change-password/", ChangePasswordView.as_view(), name="auth_change_password"),
    path("refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="auth_2fa_setup"),
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="auth_2fa_verify"),
    path("2fa/challenge/", TwoFactorChallengeView.as_view(), name="auth_2fa_challenge"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="auth_2fa_disable"),
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