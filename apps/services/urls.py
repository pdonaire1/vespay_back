from rest_framework.routers import DefaultRouter

from .views import BillServiceViewSet, ServiceSubscriptionViewSet

router = DefaultRouter()
router.register("catalog", BillServiceViewSet, basename="bill-service")
router.register("subscriptions", ServiceSubscriptionViewSet, basename="service-subscription")

urlpatterns = router.urls
