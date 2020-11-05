from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/donations/', consumers.DonationConsumer.as_asgi()),
    path('ws/ping/', consumers.PingConsumer.as_asgi()),
    path('ws/celery/', consumers.CeleryConsumer.as_asgi()),
]
