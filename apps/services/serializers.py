from rest_framework import serializers

from .models import BillService, ServiceSubscription


class BillServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillService
        fields = ("id", "name", "code", "is_active")
        read_only_fields = ("id",)


class ServiceSubscriptionSerializer(serializers.ModelSerializer):
    service_code = serializers.CharField(source="service.code", read_only=True)

    class Meta:
        model = ServiceSubscription
        fields = (
            "id",
            "service",
            "service_code",
            "contract_number",
            "linked_account",
            "auto_pay",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
