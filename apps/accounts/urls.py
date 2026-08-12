from rest_framework.routers import DefaultRouter

from .views import LinkedAccountViewSet

router = DefaultRouter()
router.register("", LinkedAccountViewSet, basename="linked-account")

urlpatterns = router.urls
