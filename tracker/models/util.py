from django.db import OperationalError


def LatestEvent():
    from tracker.models import Event

    if Event.objects.exists():
        try:
            return Event.objects.latest()
        except (Event.DoesNotExist, OperationalError):
            return None
    return None
