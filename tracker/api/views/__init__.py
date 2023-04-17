"""Define class based views for the various API views."""

import logging

from rest_framework import viewsets
from rest_framework.response import Response

from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import (
    EventSerializer,
    RunnerSerializer,
    SpeedRunSerializer,
)
from tracker.models.event import Event, Runner, SpeedRun

log = logging.getLogger(__name__)


class FlatteningViewSetMixin(object):
    """Override a view set's data query methods in order to have a flat dictionary of objects
    rather than the REST default of a nested tree.
    """

    def list(self, request, *args, **kwargs):
        """Change the response type to be a dictionary if flat related objects have been requested."""
        log.debug('query params: %s', request.query_params)
        flatten = request.query_params.get('include', None)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)

        log.debug(serializer.data)
        # if we need to flatten, it's time to walk this dictionary
        if flatten:
            targets = flatten.split(',')
            prepared_data = self._flatten_data(serializer.data, targets)
        else:
            prepared_data = serializer.data

        log.debug(prepared_data)
        return self.get_paginated_response(prepared_data)

    def retrieve(self, request, *args, **kwargs):
        """Change the response type to be a dictionary if flat related objects have been requested."""
        log.debug('query params: %s', request.query_params)

        instance = self.get_object()

        serializer = self.get_serializer(instance)

        log.debug(serializer.data)

        flatten = request.query_params.get('include', None)

        # if we need to flatten, it's time to walk this dictionary
        if flatten:
            targets = flatten.split(',')
            prepared_data = self._flatten_data([serializer.data], targets)
        else:
            prepared_data = serializer.data

        log.debug(prepared_data)
        return Response(prepared_data)

    @staticmethod
    def _flatten_data(initial_data, targets):
        log.debug('targets for flattening: %s', targets)

        primary_objs = list()
        obj_label = None
        for item in initial_data:
            obj_label = '{0:s}s'.format(item['type'])
            primary_objs.append(dict(item))

        prepared_data = {obj_label: primary_objs}

        for which in targets:
            log.debug('searching for target %s', which)
            target_objs = dict()
            for item in primary_objs:
                log.debug('searching in %s', item)
                hits = item.get(which, [])
                if hits:
                    # winch this into a list if it isn't a many=True field)
                    if not isinstance(hits, list):
                        log.debug('winching %s into a list', hits)
                        hits = [hits]

                    new_hit_list = list()
                    for hit in hits:
                        log.debug('found a hit: %s', hit)
                        target_objs[hit['id']] = hit
                        new_hit_list.append(hit['id'])
                    item[which] = new_hit_list
            prepared_data[which] = list(target_objs.values())

        return prepared_data


class EventNestedMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        event_pk = self.kwargs.get('event_pk', None)
        if event_pk:
            event = EventViewSet(
                kwargs={'pk': event_pk}, request=self.request
            ).get_object()
            queryset = self.get_event_filter(queryset, event)
        return queryset

    def get_event_filter(self, queryset, event):
        return queryset.filter(event=event)


class EventViewSet(FlatteningViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    pagination_class = TrackerPagination


class RunnerViewSet(
    FlatteningViewSetMixin, EventNestedMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer
    pagination_class = TrackerPagination

    def get_event_filter(self, queryset, event):
        return queryset.filter(speedrun__event=event)


class SpeedRunViewSet(
    FlatteningViewSetMixin, EventNestedMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = SpeedRun.objects.select_related('event').prefetch_related(
        'runners', 'hosts', 'commentators'
    )
    serializer_class = SpeedRunSerializer
    pagination_class = TrackerPagination
