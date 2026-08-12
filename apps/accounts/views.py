from rest_framework import viewsets

from .models import LinkedAccount
from .serializers import LinkedAccountSerializer


class LinkedAccountViewSet(viewsets.ModelViewSet):
    serializer_class = LinkedAccountSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return LinkedAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
