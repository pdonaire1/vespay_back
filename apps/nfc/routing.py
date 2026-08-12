from django.urls import path

from .consumers import NFCConsumer

websocket_urlpatterns = [
    path("ws/nfc/<uuid:session_id>/", NFCConsumer.as_asgi()),
]
