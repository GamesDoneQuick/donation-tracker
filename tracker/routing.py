from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/donations/', consumers.DonationConsumer),
    path('ws/ping/', consumers.PingConsumer),
]
