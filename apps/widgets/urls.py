from rest_framework.routers import DefaultRouter

from .views import ThirdPartyAppViewSet

router = DefaultRouter()
router.register("", ThirdPartyAppViewSet, basename="third-party-app")

urlpatterns = router.urls
