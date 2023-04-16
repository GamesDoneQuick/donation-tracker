from django.urls import path

from . import consumers


def channel_six(consumer):
    as_asgi = getattr(consumer, 'as_asgi', None)
    if callable(as_asgi):
        return as_asgi()
    else:
        return consumer


websocket_urlpatterns = [
    path('ws/celery/', channel_six(consumers.CeleryConsumer)),
    path('ws/donations/', channel_six(consumers.DonationConsumer)),
    path('ws/ping/', channel_six(consumers.PingConsumer)),
    path('ws/processing/', channel_six(consumers.ProcessingConsumer)),
]
