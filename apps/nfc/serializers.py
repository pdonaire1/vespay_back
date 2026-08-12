from rest_framework import serializers


class PayeeTokenCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=3, default="USD")


class ProcessPaymentSerializer(serializers.Serializer):
    payer_token = serializers.CharField()
    payee_token = serializers.CharField()
