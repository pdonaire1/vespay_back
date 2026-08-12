from django.conf import settings
from django.db import models

from apps.accounts.models import LinkedAccount
from common.models import TimeStampedModel, UUIDModel


class BillService(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ServiceSubscription(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(BillService, on_delete=models.CASCADE)
    contract_number = models.CharField(max_length=100)
    linked_account = models.ForeignKey(
        LinkedAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    auto_pay = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "service", "contract_number"],
                name="unique_subscription_per_contract",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service.code} · {self.contract_number}"
