from django.contrib import admin

from .models import FeeRule, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender",
        "recipient",
        "method",
        "amount",
        "currency",
        "status",
        "fee",
        "created_at",
    )
    list_filter = ("method", "status", "currency")
    search_fields = ("sender__email", "recipient__email", "external_transaction_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(FeeRule)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = ("app_id", "percentage", "fixed_amount", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("app_id",)
