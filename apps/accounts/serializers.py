from rest_framework import serializers

from .models import LinkedAccount


class LinkedAccountSerializer(serializers.ModelSerializer):
    credentials = serializers.JSONField(write_only=True, required=False)
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = LinkedAccount
        fields = (
            "id",
            "method",
            "method_display",
            "label",
            "credentials",
            "is_active",
            "is_default",
            "is_verified",
            "usage_count",
            "created_at",
        )
        read_only_fields = ("id", "is_verified", "usage_count", "created_at")

    def create(self, validated_data):
        credentials = validated_data.pop("credentials", {})
        account: LinkedAccount = super().create(validated_data)
        if credentials:
            account.set_credentials(credentials)
            account.save(update_fields=["credentials_encrypted"])
        return account
