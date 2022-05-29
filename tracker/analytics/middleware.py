import asyncio
from datetime import datetime

from tracker.analytics import analytics, AnalyticsEventTypes


def AnalyticsMiddleware(get_response):
    def track_request(request, started, finished):
        analytics.track(
            AnalyticsEventTypes.REQUEST_SERVED,
            {
                'timestamp': started,
                'duration': finished - started,
                'path': request.path,
                'method': request.method,
                'content_type': request.content_type,
            },
        )

    if asyncio.iscoroutinefunction(get_response):

        async def async_middleware(request):
            started = datetime.utcnow()
            response = await get_response(request)
            finished = datetime.utcnow()
            track_request(request, started, finished)
            return response

        return async_middleware

    else:

        def sync_middleware(request):
            started = datetime.utcnow()
            response = get_response(request)
            finished = datetime.utcnow()
            track_request(request, started, finished)
            return response

        return sync_middleware


# TODO: The `sync_and_async_middleware` decorator is not available on all versions
# of Django that we currently support. This has the same effect, but should change
# to use the decorator once Django 2.2 support is dropped.
AnalyticsMiddleware.async_capable = True
AnalyticsMiddleware.sync_capable = True
