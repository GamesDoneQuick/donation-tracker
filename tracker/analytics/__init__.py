from contextlib import contextmanager

from django.conf import settings

from tracker.analytics.client import AnalyticsClient
from tracker.analytics.events import AnalyticsEventTypes  # noqa: F401


analytics = AnalyticsClient(
    AnalyticsClient.Config(
        access_key=getattr(settings, 'TRACKER_ANALYTICS_ACCESS_KEY', None),
        ingest_host=getattr(settings, 'TRACKER_ANALYTICS_INGEST_HOST', ''),
        test_mode=getattr(settings, 'TRACKER_ANALYTICS_TEST_MODE', False),
        no_emit=getattr(settings, 'TRACKER_ANALYTICS_NO_EMIT', True),
    )
)


@contextmanager
def analytics_context(client: AnalyticsClient):
    try:
        yield client
    finally:
        client.flush()
