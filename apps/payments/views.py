from django.db.models import Q
from rest_framework import mixins, viewsets

from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(Q(sender=user) | Q(recipient=user))
