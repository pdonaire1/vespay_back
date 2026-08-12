from django.urls import path

from .views import PayeeTokenView, PayerTokenView, ProcessPaymentView

urlpatterns = [
    path("payer-token", PayerTokenView.as_view(), name="payer-token"),
    path("payee-token", PayeeTokenView.as_view(), name="payee-token"),
    path("process-payment", ProcessPaymentView.as_view(), name="process-payment"),
]
