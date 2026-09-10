from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    has_usable_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "cedula",
            "is_email_verified",
            "is_2fa_enabled",
            "has_usable_password",
        )
        read_only_fields = ("id", "email")

    def get_has_usable_password(self, obj) -> bool:
        return obj.has_usable_password()


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = ("id", "email", "full_name", "phone", "cedula", "password")