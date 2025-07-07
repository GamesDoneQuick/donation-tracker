from django.utils.decorators import method_decorator

from tracker.api.filters import PrizeFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import (
    PrizeFeedPermission,
    PrizeLifecyclePermission,
    PrizeStatePermission,
)
from tracker.api.serializers import PrizeSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.api.views.decorators import cache_page_for_public
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
    permission_classes = [
        PrizeFeedPermission,
        PrizeLifecyclePermission,
        PrizeStatePermission,
    ]
    filter_backends = [PrizeFilter]
    pagination_class = TrackerPagination

    @method_decorator(cache_page_for_public(60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'lifecycle' in self.request.query_params:
            queryset = queryset.time_annotation().claim_annotations(
                self.request.query_params.get('time', None)
            )
        return queryset

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(
            *args, lifecycle='lifecycle' in self.request.query_params, **kwargs
        )

    # TODO: how should draft events interact with prizes? should prizes be submittable? should they be able to be
    #  accepted? should they come back from the API if accepted but the event is still a draft?
    # for now the answer is: yes, yes, and no, since it's the least amount of changes both from a code perspective
    #  and for how things are done in practice

    def get_feed(self):
        return self.kwargs.get('feed', None)
