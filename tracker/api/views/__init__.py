"""Define class based views for the various API views."""

import contextlib
import json
import logging
from decimal import Decimal

from django.db.models import Model
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.relations import ManyRelatedField
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer

from tracker import logutil, models, settings
from tracker.api import messages
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import EventLockedPermission
from tracker.api.serializers import EventSerializer

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


class WithSerializerPermissionsMixin:
    """
    a mixin that ensures the serializer is passed the user's permissions, to determine which
    fields should be allowed to be included
    """

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(
            *args, with_permissions=self.request.user.get_all_permissions(), **kwargs
        )


class EventNestedMixin:
    def get_permissions(self):
        return super().get_permissions() + [EventLockedPermission()]

    def get_queryset(self):
        return self.get_event_filter(
            super().get_queryset(), self.get_event_from_request()
        )

    def get_event_filter(self, queryset, event):
        if event:
            queryset = queryset.filter(event=event)
        return queryset

    def get_event_from_request(self):
        if event_pk := self.kwargs.get('event_pk', None):
            return EventViewSet(
                kwargs={'pk': event_pk, 'skip_annotations': True}, request=self.request
            ).get_object()
        if (
            not self.detail
            and isinstance(self.request.data, dict)
            and (event := self.request.data.get('event', None))
        ):
            with contextlib.suppress(TypeError, ValueError):
                return models.Event.objects.filter(pk=event).first()
        return None

    def is_event_locked(self, obj=None):
        if self.detail and obj:
            event = obj.event
            # happens if trying patch an object to another event in any way
            if (
                other_event := self.request.data.get('event', None)
            ) is not None and other_event != event.pk:
                try:
                    other_event = models.Event.objects.get(pk=other_event)
                except (TypeError, ValueError, models.Event.DoesNotExist):
                    pass  # should be caught by validation later
                else:
                    return event.locked or other_event.locked
            return event.locked
        else:
            return (event := self.get_event_from_request()) is not None and event.locked


def generic_404(exception_handler):
    def _inner(exc, context):
        # override the default messaging for 404s
        if isinstance(exc, Http404):
            exc = NotFound(detail=messages.GENERIC_NOT_FOUND)
        if isinstance(exc, NotFound) and exc.detail == NotFound.default_detail:
            exc.detail = messages.GENERIC_NOT_FOUND
        return exception_handler(exc, context)

    return _inner


def normalize_json_value(value):
    if isinstance(value, Model):
        return value.pk
    elif isinstance(value, Decimal):
        return str(value)
    raise TypeError(f'expected a Model or Decimal, got {type(value)}')


class TrackerCreateMixin(mixins.CreateModelMixin):
    def perform_create(self, serializer):
        super().perform_create(serializer)
        logutil.addition(self.request, serializer.instance)

    @action(methods=['post'], detail=False, url_path='validate')
    def validate_create(self, request, *args, **kwargs):
        status_code = status.HTTP_202_ACCEPTED
        if isinstance(request.data, dict):
            data = request.data
            self.get_serializer(data=request.data).is_valid(raise_exception=True)
        elif isinstance(request.data, list):
            data = {
                'valid': [None] * len(request.data),
                'invalid': [None] * len(request.data),
            }
            for n, i in enumerate(request.data):
                try:
                    self.get_serializer(data=i).is_valid(raise_exception=True)
                except ValidationError as e:
                    data['invalid'][n] = e.detail
                    status_code = status.HTTP_400_BAD_REQUEST
                else:
                    data['valid'][n] = i
        else:
            raise ValidationError('data must be dict or list')
        return Response(data, status=status_code)


class EventCreateNestedMixin(EventNestedMixin, TrackerCreateMixin):
    pass


class TrackerUpdateMixin(mixins.UpdateModelMixin):
    @property
    def allowed_methods(self):
        # partial updates only
        return [m for m in super()._allowed_methods() if m != 'PUT']

    @action(methods=['patch'], detail=True, url_path='validate')
    def validate_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def perform_update(self, serializer):
        old_values = {}
        for key, value in serializer.initial_data.items():
            if key not in serializer.fields:
                continue
            field = serializer.fields[key]
            if isinstance(field, (ManyRelatedField, ListSerializer)):
                old_values[key] = field.to_representation(
                    getattr(serializer.instance, key).all()
                )
            else:
                old_values[key] = getattr(serializer.instance, key)
                if isinstance(old_values[key], Model):
                    old_values[key] = old_values[key].pk
        super().perform_update(serializer)
        changed_values = {}
        for key, value in old_values.items():
            if key not in serializer.data:
                continue  # happens with certain nested urls
            new_value = serializer.data[key]
            if isinstance(new_value, list):
                # this is a bit tricky since either one or both could be blank, but we need to handle lists
                #  of models vs lists of ids
                assert isinstance(
                    value, list
                ), f'expected two lists, but got {type(value)} for old value instead'
                if len(value) == 0 and len(new_value) == 0:
                    continue
                first = (value or new_value)[0]
                # TODO: sanity check to make sure they're both the same types, but that's a programming error, not a
                #  user error
                if isinstance(first, dict):
                    value = {str(m['id']) for m in value}
                    new_value = {str(m['id']) for m in new_value}
                elif isinstance(first, int):
                    value = {str(i) for i in value}
                    new_value = {str(i) for i in new_value}
                else:
                    assert isinstance(
                        first, str
                    ), f'expected dict, str, or int, got {type(first)}'
                if value != new_value:
                    changed_values[key] = {
                        'old': ','.join(value),
                        'new': ','.join(new_value),
                    }
            elif value != new_value:
                changed_values[key] = {'old': value, 'new': new_value}
        if changed_values:
            logutil.change(
                self.request,
                serializer.instance,
                json.dumps(changed_values, default=normalize_json_value),
            )


class RemoveBrowsableMixin:
    def get_renderers(self):
        return [
            r
            for r in super().get_renderers()
            if settings.TRACKER_ENABLE_BROWSABLE_API
            or not isinstance(r, BrowsableAPIRenderer)
        ]


class TrackerReadViewSet(RemoveBrowsableMixin, viewsets.ReadOnlyModelViewSet):
    # to allow action decorator to override standard permissions
    # e.g.
    # @action(methods=['patch'], permissions_classes=[CanApproveBids], include_tracker_permissions=False)
    include_tracker_permissions = True

    def get_permissions(self):
        return super().get_permissions() + (
            [DjangoModelPermissionsOrAnonReadOnly()]
            if self.include_tracker_permissions
            else []
        )

    def permission_denied(self, request, message=None, code=None):
        if code == messages.UNAUTHORIZED_OBJECT_CODE:
            raise Http404
        else:
            super().permission_denied(request, message=message, code=code)

    def get_exception_handler(self):
        return generic_404(super().get_exception_handler())


class TrackerFullViewSet(TrackerCreateMixin, TrackerUpdateMixin, TrackerReadViewSet):
    pass


class EventViewSet(FlatteningViewSetMixin, TrackerReadViewSet):
    queryset = models.Event.objects
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
