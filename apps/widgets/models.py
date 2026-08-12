from django.conf import settings
from django.db import models

from common.models import TimeStampedModel, UUIDModel
from common.utils.crypto import decrypt_field, encrypt_field


class ThirdPartyApp(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    app_id = models.CharField(max_length=64, unique=True)
    api_key_encrypted = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.app_id})"

    def set_api_key(self, api_key: str) -> None:
        self.api_key_encrypted = encrypt_field(api_key)

    def get_api_key(self) -> str:
        return decrypt_field(self.api_key_encrypted) if self.api_key_encrypted else ""


class WebhookEvent(UUIDModel, TimeStampedModel):
    app = models.ForeignKey(ThirdPartyApp, on_delete=models.CASCADE, related_name="webhooks")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    attempts = models.PositiveIntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} · {self.app.app_id}"
