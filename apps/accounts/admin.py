from django.contrib import admin

from .models import LinkedAccount


@admin.register(LinkedAccount)
class LinkedAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "method",
        "is_active",
        "is_default",
        "is_verified",
        "usage_count",
        "created_at",
    )
    list_filter = ("method", "is_active", "is_default", "is_verified")
    search_fields = ("user__email", "label")
    readonly_fields = ("credentials_encrypted", "created_at", "updated_at")
