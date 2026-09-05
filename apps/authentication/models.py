import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel

RESEND_THROTTLE_SECONDS = 30

OTP_LIFETIME_MINUTES = 15


class EmailVerification(TimeStampedModel):
    """Tracks a hashed short-lived OTP issued for an email address."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    email = models.EmailField()
    otp_hash = models.CharField(max_length=255, editable=False)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        status = "used" if self.is_used else ("expired" if self.is_expired else "active")
        return f"OTP {status} for {self.email}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def matches(self, code: str) -> bool:
        return check_password(code, self.otp_hash)

    @classmethod
    def issue(cls, user, email: str) -> tuple["EmailVerification", str]:
        """Invalidates previous pending codes and returns a fresh (record, plain code)."""
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f"{secrets.randbelow(1_000_000):06d}"
        verification = cls.objects.create(
            user=user,
            email=email,
            otp_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=OTP_LIFETIME_MINUTES),
        )
        return verification, code