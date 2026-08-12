import json

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel, UUIDModel
from common.utils.crypto import decrypt_field, encrypt_field


class PaymentMethod(models.TextChoices):
    PAYPAL = "PAYPAL", "PayPal"
    BINANCE = "BINANCE", "Binance Pay"
    PAGO_MOVIL = "PAGO_MOVIL", "Pago Móvil"
    ZELLE = "ZELLE", "Zelle"
    CREDIT_CARD = "CREDIT_CARD", "Tarjeta de crédito"
    BANK_TRANSFER = "BANK_TRANSFER", "Transferencia bancaria"


class LinkedAccount(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linked_accounts",
    )
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    label = models.CharField(max_length=100, blank=True)
    credentials_encrypted = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "method"],
                name="unique_account_per_method",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} · {self.get_method_display()}"

    def set_credentials(self, credentials: dict) -> None:
        self.credentials_encrypted = encrypt_field(json.dumps(credentials))

    def get_credentials(self) -> dict:
        if not self.credentials_encrypted:
            return {}
        return json.loads(decrypt_field(self.credentials_encrypted))
