from django.utils.decorators import method_decorator

from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import PrivateGenericPermissions
from tracker.api.serializers import MilestoneSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.api.views.decorators import cache_page_for_public
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

    @method_decorator(cache_page_for_public(60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def _include_hidden(self, instance=None):
        return (
            isinstance(instance, Milestone) and instance.visible
        ) or 'all' in self.request.query_params

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.detail or 'all' in self.request.query_params):
            queryset = queryset.filter(visible=True)
        return queryset
