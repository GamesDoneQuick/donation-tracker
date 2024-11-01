import logging

from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import PrivateGenericPermissions
from tracker.api.serializers import InterviewSerializer
from tracker.api.views import EventCreateNestedMixin, TrackerFullViewSet
from tracker.models import Interview

logger = logging.getLogger(__name__)


class InterviewViewSet(TrackerFullViewSet, EventCreateNestedMixin):
    queryset = Interview.objects.select_related('event')
    serializer_class = InterviewSerializer
    pagination_class = TrackerPagination
    permission_classes = [*PrivateGenericPermissions('interview', lambda o: o.public)]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.detail or 'all' in self.request.query_params):
            queryset = queryset.filter(public=True)
        return queryset
