from django.conf import settings
from django.db import models

from apps.accounts.models import PaymentMethod
from common.models import TimeStampedModel, UUIDModel


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    PROCESSING = "PROCESSING", "Procesando"
    COMPLETED = "COMPLETED", "Completado"
    FAILED = "FAILED", "Fallido"


class Transaction(UUIDModel, TimeStampedModel):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_transactions",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_transactions",
    )
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    external_transaction_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.amount} {self.currency} · {self.method} · {self.status}"


class FeeRule(TimeStampedModel):
    app_id = models.CharField(max_length=64, null=True, blank=True)
    percentage = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["app_id", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["app_id"],
                name="unique_fee_rule_per_app",
            ),
        ]

    def __str__(self) -> str:
        scope = self.app_id or "global"
        return f"{scope} · {self.percentage}% + {self.fixed_amount}"
