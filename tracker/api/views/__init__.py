"""Define class based views for the various API views."""
import json
import logging

from django.db.models import Model
from django.http import Http404
from rest_framework import mixins, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response

from tracker import logutil, settings
from tracker.api import messages
from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import EventSerializer
from tracker.models.event import Event

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


class WithPermissionsMixin:
    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(
            *args, with_permissions=self.request.user.get_all_permissions(), **kwargs
        )


class EventNestedMixin:
    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(
            *args, event_pk=self.kwargs.get('event_pk', None), **kwargs
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        event_pk = self.kwargs.get('event_pk', None)
        if event_pk:
            event = EventViewSet(
                kwargs={'pk': event_pk, 'skip_annotations': True}, request=self.request
            ).get_object()
            queryset = self.get_event_filter(queryset, event)
        return queryset

    def get_event_filter(self, queryset, event):
        return queryset.filter(event=event)

    def get_event_from_request(self, request):
        if 'event' in request.data:
            try:
                return Event.objects.filter(pk=request.data['event']).first()
            except (TypeError, ValueError):
                pass
        return None

    def is_event_locked(self, request):
        event = self.get_event_from_request(request)
        return event and event.locked


def generic_404(exception_handler):
    def _inner(exc, context):
        # override the default messaging for 404s
        if isinstance(exc, Http404):
            exc = NotFound(detail=messages.GENERIC_NOT_FOUND)
        if isinstance(exc, NotFound) and exc.detail == NotFound.default_detail:
            exc.detail = messages.GENERIC_NOT_FOUND
        return exception_handler(exc, context)

    return _inner


def model_to_pk(model):
    if isinstance(model, Model):
        return model.pk
    raise TypeError


class TrackerCreateMixin(mixins.CreateModelMixin):
    def perform_create(self, serializer):
        super().perform_create(serializer)
        logutil.addition(self.request, serializer.instance)


class TrackerUpdateMixin(mixins.UpdateModelMixin):
    def perform_update(self, serializer):
        old_values = {}
        for key, value in serializer.initial_data.items():
            if key not in serializer.fields:
                continue
            old_values[key] = getattr(serializer.instance, key)
            if isinstance(old_values[key], Model):
                old_values[key] = old_values[key].pk
        super().perform_update(serializer)
        changed_values = {}
        for key, value in old_values.items():
            if value != serializer.data[key]:
                changed_values[key] = {'old': value, 'new': serializer.data[key]}
        if changed_values:
            logutil.change(
                self.request,
                serializer.instance,
                json.dumps(changed_values, default=model_to_pk),
            )


class TrackerReadViewSet(viewsets.ReadOnlyModelViewSet):
    def get_renderers(self):
        return [
            r
            for r in super().get_renderers()
            if settings.TRACKER_ENABLE_BROWSABLE_API
            or not isinstance(r, BrowsableAPIRenderer)
        ]

    def permission_denied(self, request, message=None, code=None):
        if code == messages.UNAUTHORIZED_OBJECT_CODE:
            raise Http404
        else:
            super().permission_denied(request, message=message, code=code)

    def get_exception_handler(self):
        return generic_404(super().get_exception_handler())


class EventViewSet(FlatteningViewSetMixin, TrackerReadViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    pagination_class = TrackerPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.kwargs.get('skip_annotations', False):
            queryset = queryset.with_annotations()
        return queryset

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        with_totals = self.request.query_params.get('totals') is not None
        return serializer_class(*args, **kwargs, with_totals=with_totals)
