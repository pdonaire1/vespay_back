from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "sender",
            "recipient",
            "method",
            "method_display",
            "amount",
            "currency",
            "status",
            "status_display",
            "fee",
            "net_amount",
            "external_transaction_id",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "fee",
            "net_amount",
            "external_transaction_id",
            "created_at",
        )
