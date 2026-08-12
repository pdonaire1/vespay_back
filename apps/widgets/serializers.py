from rest_framework import serializers

from .models import ThirdPartyApp


class ThirdPartyAppSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ThirdPartyApp
        fields = ("id", "name", "app_id", "api_key", "webhook_url", "is_active", "created_at")
        read_only_fields = ("id", "app_id", "created_at")

    def create(self, validated_data):
        api_key = validated_data.pop("api_key", "")
        app: ThirdPartyApp = super().create(validated_data)
        if api_key:
            app.set_api_key(api_key)
            app.save(update_fields=["api_key_encrypted"])
        return app
