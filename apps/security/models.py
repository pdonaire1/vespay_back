from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class UserBiometricCredential(TimeStampedModel):
    """Credencial WebAuthn (passkey) registrada por un dispositivo del usuario."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="biometric_credentials",
    )
    credential_id = models.CharField(max_length=512, unique=True, db_index=True)
    public_key = models.TextField()
    sign_count = models.BigIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    device_name = models.CharField(max_length=100, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_biometric_credentials"
        ordering = ("-created_at",)
        verbose_name = "credencial biométrica"
        verbose_name_plural = "credenciales biométricas"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.credential_id[:12]}"
