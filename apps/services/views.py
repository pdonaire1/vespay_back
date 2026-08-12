from rest_framework import mixins, viewsets

from .models import BillService, ServiceSubscription
from .serializers import BillServiceSerializer, ServiceSubscriptionSerializer


class BillServiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BillServiceSerializer
    queryset = BillService.objects.filter(is_active=True)
    http_method_names = ["get", "head", "options"]


class ServiceSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSubscriptionSerializer

    def get_queryset(self):
        return ServiceSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
