from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import RunnerSerializer
from tracker.api.views import (
    EventNestedMixin,
    FlatteningViewSetMixin,
    TrackerReadViewSet,
)
from tracker.models import Runner


class RunnerViewSet(FlatteningViewSetMixin, EventNestedMixin, TrackerReadViewSet):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer
    pagination_class = TrackerPagination

    def get_event_filter(self, queryset, event):
        return queryset.filter(speedrun__event=event).distinct()
