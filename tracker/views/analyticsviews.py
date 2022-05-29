import json

from django.http.response import HttpResponse
from django.views.decorators.http import require_POST

from tracker.analytics import analytics

__all__ = [
    'post_analytics',
]


@require_POST
def post_analytics(request):
    events = json.loads(request.body)

    for event in events:
        event_name = event.get('event_name', None)
        properties = event.get('properties', None)
        if event_name is None or properties is None:
            next

        analytics.track_generic(event_name, properties)

    # This is intentionally opaque to avoid leaking any event validations
    # or configurations about how events are processed.
    return HttpResponse(status=204)
