from django.contrib import admin

from .models import BillService, ServiceSubscription


@admin.register(BillService)
class BillServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(ServiceSubscription)
class ServiceSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "service", "contract_number", "auto_pay", "is_active")
    list_filter = ("auto_pay", "is_active", "service")
    search_fields = ("user__email", "contract_number")
    readonly_fields = ("created_at", "updated_at")
