from django.urls import path

from .views import (
    BiometricChallengeView,
    BiometricRegisterOptionsView,
    BiometricRegisterVerifyView,
    BiometricVerifyView,
)

urlpatterns = [
    path(
        "biometric/register/",
        BiometricRegisterOptionsView.as_view(),
        name="biometric_register",
    ),
    path(
        "biometric/register/verify/",
        BiometricRegisterVerifyView.as_view(),
        name="biometric_register_verify",
    ),
    path(
        "biometric/challenge/",
        BiometricChallengeView.as_view(),
        name="biometric_challenge",
    ),
    path("biometric/verify/", BiometricVerifyView.as_view(), name="biometric_verify"),
]
