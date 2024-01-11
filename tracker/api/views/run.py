from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import TechNotesPermission
from tracker.api.serializers import SpeedRunSerializer
from tracker.api.views import (
    EventNestedMixin,
    FlatteningViewSetMixin,
    TrackerReadViewSet,
    WithPermissionsMixin,
)
from tracker.models import SpeedRun


class SpeedRunViewSet(
    FlatteningViewSetMixin,
    WithPermissionsMixin,
    EventNestedMixin,
    TrackerReadViewSet,
):
    queryset = SpeedRun.objects.select_related('event').prefetch_related(
        'runners', 'hosts', 'commentators', 'video_links'
    )
    serializer_class = SpeedRunSerializer
    pagination_class = TrackerPagination
    permission_classes = [TechNotesPermission]

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(
            *args, with_tech_notes='tech_notes' in self.request.query_params, **kwargs
        )
