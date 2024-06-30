import logging

from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import (
    PrivateInterviewDetailPermission,
    PrivateInterviewListPermission,
)
from tracker.api.serializers import InterviewSerializer
from tracker.api.views import EventNestedMixin, TrackerReadViewSet
from tracker.models import Interview

logger = logging.getLogger(__name__)


class InterviewViewSet(
    EventNestedMixin,
    TrackerReadViewSet,
):
    queryset = Interview.objects.select_related('event').prefetch_related('tags')
    serializer_class = InterviewSerializer
    pagination_class = TrackerPagination
    permission_classes = [
        PrivateInterviewDetailPermission,
        PrivateInterviewListPermission,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.detail or 'all' in self.request.query_params):
            queryset = queryset.filter(public=True)
        return queryset
