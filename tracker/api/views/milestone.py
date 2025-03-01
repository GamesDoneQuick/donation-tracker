from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import PrivateGenericPermissions
from tracker.api.serializers import MilestoneSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.models import Milestone


class MilestoneViewSet(
    WithSerializerPermissionsMixin,
    EventNestedMixin,
    TrackerFullViewSet,
):
    queryset = Milestone.objects.select_related('event')
    serializer_class = MilestoneSerializer
    pagination_class = TrackerPagination
    permission_classes = [
        *PrivateGenericPermissions('milestone', lambda o: o.visible),
    ]

    def _include_hidden(self, instance=None):
        return (
            isinstance(instance, Milestone) and instance.visible
        ) or 'all' in self.request.query_params

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.detail or 'all' in self.request.query_params):
            queryset = queryset.filter(visible=True)
        return queryset
