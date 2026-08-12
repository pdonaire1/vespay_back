from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel


class NFCStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    COMPLETED = "COMPLETED", "Completado"
    FAILED = "FAILED", "Fallido"


class TokenState(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    USED = "USED", "Usado"
    EXPIRED = "EXPIRED", "Expirado"


def default_expiry():
    return timezone.now() + timedelta(seconds=settings.VESPAY_NFC_TOKEN_TTL)


class PayerToken(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField(default=default_expiry)
    state = models.CharField(max_length=10, choices=TokenState.choices, default=TokenState.PENDING)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class PayeeToken(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    expires_at = models.DateTimeField(default=default_expiry)
    state = models.CharField(max_length=10, choices=TokenState.choices, default=TokenState.PENDING)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class NFCSession(UUIDModel, TimeStampedModel):
    payer_token = models.OneToOneField(PayerToken, on_delete=models.CASCADE)
    payee_token = models.OneToOneField(PayeeToken, on_delete=models.CASCADE)
    transaction = models.OneToOneField(
        "payments.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=10, choices=NFCStatus.choices, default=NFCStatus.PENDING)

    def __str__(self) -> str:
        return f"{self.id} · {self.status}"
