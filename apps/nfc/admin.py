from django.contrib import admin

from .models import NFCSession, PayeeToken, PayerToken


@admin.register(PayerToken)
class PayerTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "state", "expires_at")
    list_filter = ("state",)
    readonly_fields = ("token", "expires_at")


@admin.register(PayeeToken)
class PayeeTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "state", "expires_at")
    list_filter = ("state", "currency")
    readonly_fields = ("token", "expires_at")


@admin.register(NFCSession)
class NFCSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "transaction", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at")
