from django.contrib import admin

from .models import ThirdPartyApp, WebhookEvent


@admin.register(ThirdPartyApp)
class ThirdPartyAppAdmin(admin.ModelAdmin):
    list_display = ("name", "app_id", "owner", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "app_id", "owner__email")
    readonly_fields = ("app_id", "created_at", "updated_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "app", "attempts", "delivered_at", "created_at")
    list_filter = ("event_type",)
    search_fields = ("app__app_id",)
    readonly_fields = ("created_at", "updated_at")
