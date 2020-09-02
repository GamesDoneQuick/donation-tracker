from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/ping/', consumers.PingConsumer),
    path('ws/celery/', consumers.CeleryConsumer),
]
