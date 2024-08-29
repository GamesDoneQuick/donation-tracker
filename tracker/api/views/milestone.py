from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import EventLockedPermission, PrivateGenericPermissions
from tracker.api.serializers import MilestoneSerializer
from tracker.api.views import (
    EventCreateNestedMixin,
    TrackerReadViewSet,
    TrackerUpdateMixin,
    WithPermissionsMixin,
)
from tracker.models import Milestone


class MilestoneViewSet(
    WithPermissionsMixin,
    EventCreateNestedMixin,
    TrackerUpdateMixin,
    TrackerReadViewSet,
):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    pagination_class = TrackerPagination
    permission_classes = [
        EventLockedPermission,
        *PrivateGenericPermissions('milestone', lambda o: o.visible),
    ]

    def _include_hidden(self, instance=None):
        return (
            isinstance(instance, Milestone) and instance.visible
        ) or 'all' in self.request.query_params

    def filter_queryset(self, queryset):
        queryset = super().get_queryset()
        if not (self.detail or 'all' in self.request.query_params):
            queryset = queryset.filter(visible=True)
        return super().filter_queryset(queryset)
