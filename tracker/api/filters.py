import datetime
import logging

from django.db.models import Q
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import filters
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied

from tracker.api import messages
from tracker.models import Bid

logger = logging.getLogger(__name__)


class TrackerFilter(filters.BaseFilterBackend):
    filter_params = {}

    def filter_queryset(self, request, queryset, view):
        if not view.detail:
            if 'id' in request.query_params:
                try:
                    queryset = queryset.filter(
                        id__in=request.query_params.getlist('id')
                    )
                except (TypeError, ValueError):
                    raise ParseError(
                        detail=messages.MALFORMED_SEARCH_PARAMETER_SPECIFIC % 'id',
                        code=messages.MALFORMED_SEARCH_PARAMETER_CODE,
                    )
            filter_args = []
            filter_params = {}
            for param, filter_param in self.filter_params.items():
                if param in request.query_params:
                    if isinstance(filter_param, str):
                        if filter_param.endswith('__in'):
                            values = request.query_params.getlist(param)
                            if any(
                                not self.has_filter_permission(request, param, value)
                                for value in values
                            ):
                                raise PermissionDenied(
                                    detail=messages.UNAUTHORIZED_FILTER_PARAM,
                                    code=messages.UNAUTHORIZED_FILTER_PARAM_CODE,
                                )
                            filter_params[filter_param] = [
                                self.normalize_value(param, value) for value in values
                            ]
                        else:
                            value = request.query_params[param]
                            if not self.has_filter_permission(request, param, value):
                                raise PermissionDenied(
                                    detail=messages.UNAUTHORIZED_FILTER_PARAM,
                                    code=messages.UNAUTHORIZED_FILTER_PARAM_CODE,
                                )
                            filter_params[filter_param] = self.normalize_value(
                                param, value
                            )
                    elif isinstance(filter_param, Q):
                        filter_args.append(filter_param)
                    elif callable(filter_param):
                        filter_args.append(filter_param(request.query_params[param]))
            try:
                queryset = queryset.filter(*filter_args, **filter_params)
            except (ValueError, TypeError):
                raise ParseError(
                    detail=messages.MALFORMED_SEARCH_PARAMETER,
                    code=messages.MALFORMED_SEARCH_PARAMETER_CODE,
                )
        return queryset

    def normalize_value(self, field, value):
        return value

    def has_filter_permission(self, request, field, value):
        return True


class BidFilter(TrackerFilter):
    filter_params = {
        'name': 'name__icontains',
        'state': 'state__in',
        'run': 'speedrun__in',
        'parent': 'parent__in',
        'level': 'level',
        'target': 'istarget',
        'trunk': Q(level=0),
        'branch': ~Q(level=0) & Q(istarget=False),
        'leaf': ~Q(level=0) & Q(istarget=True),
    }

    def normalize_value(self, field, value):
        if field == 'state':
            return value.upper()
        return value

    def has_filter_permission(self, request, field, value):
        return (
            field != 'state'
            or value in Bid.PUBLIC_STATES
            or request.user.has_perm('tracker.view_hidden_bid')
        )

    def filter_queryset(self, request, queryset, view):
        feed = view.get_feed()
        query_params = request.query_params
        if feed is None:
            if not view.detail and 'state' not in query_params:
                queryset = queryset.public()
        elif feed == 'open':
            queryset = queryset.open()
        elif feed == 'closed':
            queryset = queryset.closed()
        elif feed == 'current':
            # TODO: move this to a helper when it come time to share these with runs/prizes
            feed_params = {}
            try:
                if 'min_runs' in query_params:
                    feed_params['min_runs'] = int(query_params['min_runs'])
                if 'max_runs' in query_params:
                    feed_params['max_runs'] = int(query_params['max_runs'])
                if 'delta' in query_params:
                    feed_params['delta'] = datetime.timedelta(
                        minutes=int(query_params['delta'])
                    )
                if 'now' in query_params:
                    feed_params['now'] = query_params['now']
                queryset = queryset.current(**feed_params)
            except (TypeError, ValueError):
                raise ParseError(
                    detail=messages.MALFORMED_SEARCH_PARAMETER,
                    code=messages.MALFORMED_SEARCH_PARAMETER_CODE,
                )
        elif feed in ('pending', 'all'):
            if feed == 'pending':
                queryset = queryset.pending()
            # no change for 'all'
        elif feed is not None:
            if feed.upper() in Bid.objects.ALL_FEEDS:
                logger.warning(f'unhandled valid bid feed `{feed}`')
            raise NotFound(
                detail=messages.INVALID_FEED % feed, code=messages.INVALID_FEED_CODE
            )

        if feed is not None:
            # feed makes no sense for detail views or when trying to explicitly filter by state, but for different reasons
            if view.detail:
                raise Http404
            if 'state' in query_params:
                raise ParseError(
                    detail=_('Cannot search for state while using the feed endpoint.'),
                    code=messages.INVALID_SEARCH_PARAMETER_CODE,
                )

        if view.action == 'tree':
            if feed == 'pending':
                raise NotFound(
                    detail=_('Cannot view pending feed in tree mode.'),
                    code=messages.INVALID_SEARCH_PARAMETER_CODE,
                )

            for param in ('level', 'trunk', 'branch', 'leaf'):
                if param in query_params:
                    raise ParseError(
                        detail=_('Cannot search for %s while using the tree endpoint.')
                        % param,
                        code=messages.INVALID_SEARCH_PARAMETER_CODE,
                    )

        return super().filter_queryset(request, queryset, view)
