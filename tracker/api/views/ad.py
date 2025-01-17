import logging

from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import AdSerializer
from tracker.api.views import EventCreateNestedMixin, TrackerFullViewSet
from tracker.models import Ad

logger = logging.getLogger(__name__)


class AdViewSet(TrackerFullViewSet, EventCreateNestedMixin):
    queryset = Ad.objects.select_related('event').prefetch_related(
        'tags',
    )
    serializer_class = AdSerializer
    pagination_class = TrackerPagination
    permission_classes = [tracker_permission('tracker.view_ad')]
