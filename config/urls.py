from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from config.views import AuthRedocView, AuthSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", AuthSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", AuthRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/nfc/", include("apps.nfc.urls")),
    path("api/v1/security/", include("apps.security.urls")),
    path("api/v1/widgets/", include("apps.widgets.urls")),
    path("api/v1/services/", include("apps.services.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
