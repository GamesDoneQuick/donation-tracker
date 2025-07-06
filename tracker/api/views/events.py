from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from tracker import models
from tracker.api.filters import EventFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import EventSerializer
from tracker.api.views import FlatteningViewSetMixin, TrackerReadViewSet


class EventViewSet(FlatteningViewSetMixin, TrackerReadViewSet):
    queryset = models.Event.objects
    filter_backends = [EventFilter]
    serializer_class = EventSerializer
    pagination_class = TrackerPagination

    @method_decorator(cache_page(60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().with_cache()

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        with_totals = self.request.query_params.get('totals') is not None
        return serializer_class(*args, **kwargs, with_totals=with_totals)
