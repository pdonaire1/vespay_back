import secrets

from rest_framework import viewsets

from .models import ThirdPartyApp
from .serializers import ThirdPartyAppSerializer


class ThirdPartyAppViewSet(viewsets.ModelViewSet):
    serializer_class = ThirdPartyAppSerializer

    def get_queryset(self):
        return ThirdPartyApp.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            app_id=f"app_{secrets.token_hex(8)}",
        )
