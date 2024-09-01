from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import HeadsetSerializer
from tracker.api.views import TrackerReadViewSet, TrackerUpdateMixin
from tracker.models import Headset


class HeadsetViewSet(
    TrackerUpdateMixin,
    TrackerReadViewSet,
):
    queryset = Headset.objects.all()
    serializer_class = HeadsetSerializer
    pagination_class = TrackerPagination
