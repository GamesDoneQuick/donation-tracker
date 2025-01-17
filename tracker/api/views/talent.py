from django.db.models import Q
from rest_framework.decorators import action

from tracker.api.filters import TalentFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import TalentSerializer
from tracker.api.views import (
    EventNestedMixin,
    FlatteningViewSetMixin,
    TrackerFullViewSet,
)
from tracker.api.views.run import SpeedRunViewSet
from tracker.models import Talent


class TalentViewSet(FlatteningViewSetMixin, EventNestedMixin, TrackerFullViewSet):
    queryset = Talent.objects.all()
    serializer_class = TalentSerializer
    pagination_class = TrackerPagination
    filter_backends = [TalentFilter]

    def is_event_locked(self, obj=None):
        # talent never actually belongs to an event, just associated with it
        return False

    def get_event_filter(self, queryset, event):
        if event is None:
            return queryset
        # possible FIXME: filtering at this point means that trying to query, say, a list of runs where a given
        #  person isn't participating in the event at all gives you a 404 instead of a blank list, which isn't great
        #  for consistency but I'm not sure how much of a problem it is in practice
        return queryset.filter(
            Q(runs__event=event)
            | Q(hosting__event=event)
            | Q(commentating__event=event)
        ).distinct()

    def _fetch_sublist(self, query_filter):
        # bypass the usual event filter because we're doing it already
        queryset = super().get_queryset().filter(query_filter)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def _sublist_event_filter(self, key):
        return (
            Q(**{f'{key}__event': event})
            if (event := self.get_event_from_request())
            else ~Q(**{key: None})
        )

    @action(detail=False)
    def runners(self, *args, **kwargs):
        return self._fetch_sublist(self._sublist_event_filter('runs'))

    @action(detail=False)
    def hosts(self, *args, **kwargs):
        return self._fetch_sublist(self._sublist_event_filter('hosting'))

    @action(detail=False)
    def commentators(self, *args, **kwargs):
        return self._fetch_sublist(self._sublist_event_filter('commentating'))

    # these are all m2m relationships, so we still include the nested key from the run, even though it can be
    #  partially redundant

    def _fetch_run_list(self, query_filter):
        viewset = SpeedRunViewSet(request=self.request, kwargs=self.kwargs)
        queryset = viewset.get_queryset().filter(query_filter).distinct()
        page = self.paginate_queryset(queryset)
        serializer = viewset.get_serializer_class()(
            page, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def participating(self, *args, **kwargs):
        obj = self.get_object()
        return self._fetch_run_list(Q(runners=obj) | Q(hosts=obj) | Q(commentators=obj))

    @action(detail=True)
    def runs(self, *args, **kwargs):
        return self._fetch_run_list(Q(runners=self.get_object()))

    @action(detail=True)
    def hosting(self, *args, **kwargs):
        return self._fetch_run_list(Q(hosts=self.get_object()))

    @action(detail=True)
    def commentating(self, *args, **kwargs):
        return self._fetch_run_list(Q(commentators=self.get_object()))
