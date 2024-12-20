from tracker.api.filters import PrizeFilter
from tracker.api.permissions import PrizeFeedPermission, PrizeStatePermission
from tracker.api.serializers import PrizeSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.models import Prize


class PrizeViewSet(
    WithSerializerPermissionsMixin,
    EventNestedMixin,
    TrackerFullViewSet,
):
    queryset = Prize.objects.select_related(
        'event', 'startrun', 'endrun', 'prev_run', 'next_run'
    )
    serializer_class = PrizeSerializer
    permission_classes = [PrizeFeedPermission, PrizeStatePermission]
    filter_backends = [PrizeFilter]

    def get_feed(self):
        return self.kwargs.get('feed', None)
