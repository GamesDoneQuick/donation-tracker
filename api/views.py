"""Define class based views for the various API views."""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from tracker.models.event import Event, Runner, SpeedRun
from tracker.api.serializers import EventSerializer, RunnerSerializer, SpeedRunSerializer

log = logging.getLogger(__name__)


class FlatteningViewSetMixin(object):
    """Override a view set's data query methods in order to have a flat dictionary of objects
    rather than the REST default of a nested tree.
    """

    def list(self, request):
        """Change the response type to be a dictionary if flat related objects have been requested."""
        log.debug("query params: %s", request.query_params)
        flatten = request.query_params.get('include', None)

        serializer = self.serializer_class(self.queryset, many=True)

        log.debug(serializer.data)
        # if we need to flatten, it's time to walk this dictionary
        if flatten:
            targets = flatten.split(',')
            prepared_data = self._flatten_data(serializer.data, targets)
        else:
            prepared_data = serializer.data

        log.debug(prepared_data)
        return Response(prepared_data)

    def retrieve(self, request, pk=None):
        """Change the response type to be a dictionary if flat related objects have been requested."""
        log.debug("query params: %s", request.query_params)
        flatten = request.query_params.get('include', None)

        obj = get_object_or_404(self.queryset, pk=pk)
        serializer = self.serializer_class(obj)

        log.debug(serializer.data)
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
        log.debug("targets for flattening: %s", targets)

        primary_objs = list()
        obj_label = None
        for item in initial_data:
            obj_label = '{0:s}s'.format(item['type'])
            primary_objs.append(dict(item))

        prepared_data = {
            obj_label: primary_objs
        }

        for which in targets:
            log.debug("searching for target %s", which)
            target_objs = dict()
            for item in primary_objs:
                log.debug("searching in %s", item)
                hits = item.get(which, [])
                if hits:
                    # winch this into a list if it isn't a many=True field)
                    if not isinstance(hits, list):
                        log.debug("winching %s into a list", hits)
                        hits = [hits]

                    new_hit_list = list()
                    for hit in hits:
                        log.debug("found a hit: %s", hit)
                        target_objs[hit['id']] = hit
                        new_hit_list.append(hit['id'])
                    item[which] = new_hit_list
            prepared_data[which] = target_objs.values()

        return prepared_data


class EventViewSet(FlatteningViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class RunnerViewSet(FlatteningViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer


class SpeedRunViewSet(FlatteningViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SpeedRun.objects.all()
    serializer_class = SpeedRunSerializer
