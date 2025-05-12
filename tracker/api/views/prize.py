from tracker.api.filters import PrizeFilter
from tracker.api.pagination import TrackerPagination
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
    pagination_class = TrackerPagination

    # TODO: how should draft events interact with prizes? should prizes be submittable? should they be able to be
    #  accepted? should they come back from the API if accepted but the event is still a draft?
    # for now the answer is: yes, yes, and no, since it's the least amount of changes both from a code perspective
    #  and for how things are done in practice

    def get_feed(self):
        return self.kwargs.get('feed', None)
