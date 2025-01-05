from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import PrivateGenericPermissions, TechNotesPermission
from tracker.api.serializers import SpeedRunSerializer
from tracker.api.views import (
    EventNestedMixin,
    FlatteningViewSetMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.models import SpeedRun


class SpeedRunViewSet(
    FlatteningViewSetMixin,
    WithSerializerPermissionsMixin,
    EventNestedMixin,
    TrackerFullViewSet,
):
    queryset = SpeedRun.objects.select_related(
        'event', 'priority_tag'
    ).prefetch_related(
        'runners', 'hosts', 'commentators', 'video_links__link_type', 'tags'
    )
    serializer_class = SpeedRunSerializer
    pagination_class = TrackerPagination
    permission_classes = [
        TechNotesPermission,
        *PrivateGenericPermissions('speedrun', lambda r: r.order is not None),
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.detail and 'all' not in self.request.query_params:
            queryset = queryset.exclude(order=None)
        return queryset

    def get_serializer(self, *args, **kwargs):
        with_tech_notes = (
            self.request.method == 'GET' and 'tech_notes' in self.request.query_params
        ) or (
            self.request.method in ('POST', 'PATCH')
            and 'tech_notes' in self.request.data
        )
        return super().get_serializer(*args, with_tech_notes=with_tech_notes, **kwargs)
