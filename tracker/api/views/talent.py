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
from tracker.api.views.interview import InterviewViewSet
from tracker.api.views.run import SpeedRunViewSet
from tracker.models import Talent


class TalentViewSet(FlatteningViewSetMixin, EventNestedMixin, TrackerFullViewSet):
    queryset = Talent.objects.all()
    serializer_class = TalentSerializer
    pagination_class = TrackerPagination
    filter_backends = [TalentFilter]

    def is_event_archived(self, obj=None):
        # talent never actually belongs to an event, just associated with it
        return False

    def is_event_draft(self, obj=None):
        # talent does not belong to an event, but a particular query might
        return (event := self.get_event_from_request()) is not None and event.draft

    def get_event_filter(self, queryset, event):
        if event is None:
            return queryset
        # possible FIXME: filtering at this point means that trying to query, say, a list of runs where a given
        #  person isn't participating in the event at all gives you a 404 instead of a blank list, which isn't great
        #  for consistency but I'm not sure how much of a problem it is in practice
        # using joined Q | queries here caused horrible seq scans, but this seems to work a lot better and it's unlikely
        #  that the id list will get terribly long for a single event
        return queryset.filter(
            id__in=(
                m.id
                for m in queryset.filter(runs__event=event)
                .union(queryset.filter(hosting__event=event))
                .union(queryset.filter(commentating__event=event))
                .union(queryset.filter(interviewer_for__event=event))
                .union(queryset.filter(subject_for__event=event))
            )
        )

    def get_draft_filter(self, queryset, event):
        # for eventless sublists, this is filtered in the helper
        # for eventless general query, it is fine to just list everything anyway
        return queryset

    def _fetch_sublist(self, query_filter):
        # bypass the usual event filter to not repeat ourselves
        queryset = self.queryset.filter(query_filter).distinct()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def _sublist_event_filter(self, key):
        return (
            Q(**{f'{key}__event': event})
            if (event := self.get_event_from_request())
            else (~Q(**{key: None}) & Q(**{f'{key}__event__draft': False}))
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

    @action(detail=False)
    def interviewers(self, *args, **kwargs):
        return self._fetch_sublist(self._sublist_event_filter('interviewer_for'))

    @action(detail=False)
    def subjects(self, *args, **kwargs):
        return self._fetch_sublist(self._sublist_event_filter('subject_for'))

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

    def _fetch_interview_list(self, query_filter):
        viewset = InterviewViewSet(request=self.request, kwargs=self.kwargs)
        queryset = viewset.get_queryset().filter(query_filter).distinct()
        page = self.paginate_queryset(queryset)
        serializer = viewset.get_serializer_class()(
            page, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def interviews(self, *args, **kwargs):
        obj = self.get_object()
        return self._fetch_interview_list(Q(interviewers=obj) | Q(subjects=obj))

    @action(detail=True)
    def interviewer(self, *args, **kwargs):
        return self._fetch_interview_list(Q(interviewers=self.get_object()))

    @action(detail=True)
    def subject(self, *args, **kwargs):
        return self._fetch_interview_list(Q(subjects=self.get_object()))
