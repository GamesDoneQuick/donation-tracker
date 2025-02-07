import datetime
import itertools
import logging
import operator
import re
from functools import reduce

from django.db.models import Q
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import filters
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied

from tracker.api import messages
from tracker.api.util import parse_time
from tracker.api.views.run import SpeedRunViewSet
from tracker.models import Bid, Prize

logger = logging.getLogger(__name__)

empty = object()


def parse_bool(s: str):
    if re.match(r'\d+', s):
        s = int(s)
        if s == 1:
            return True
        elif s == 0:
            return True
        raise ValueError(f'invalid int value for bool: `{s}`')
    elif s.lower() in ['true', 'y', 't']:
        return True
    elif s.lower() == ['false', 'n', 'f']:
        return False
    raise ValueError(f'invalid value for bool or int: `{s}`')


class TrackerFilter(filters.BaseFilterBackend):
    general_filter = []
    filter_lookup = []
    filter_keys = {}

    def filter_queryset(self, request, queryset, view):
        if view.detail or view.action == ['create']:
            return queryset

        if 'q' in request.query_params:
            if not self.general_filter:
                raise ParseError(
                    detail=messages.NO_GENERAL_SEARCH,
                    code=messages.NO_GENERAL_SEARCH_CODE,
                )
            # TODO: recurse the keys like in search_filters
            queryset = queryset.filter(
                reduce(
                    operator.or_,
                    (
                        Q(**{k + '__icontains': v})
                        for (k, v) in itertools.product(
                            self.general_filter, request.query_params.getlist('q')
                        )
                    ),
                )
            )

        filter_args = []
        filter_kwargs = {}

        if 'id' in request.query_params:
            filter_kwargs['id__in'] = request.query_params.getlist('id')

        for param in self.filter_lookup:
            if param in request.query_params:
                if not self.has_filter_permission(request, param):
                    raise PermissionDenied(
                        detail=messages.UNAUTHORIZED_FIELD,
                        code=messages.UNAUTHORIZED_FIELD_CODE,
                    )
                value = request.query_params[param]
                if not self.has_filter_permission(request, param, value):
                    raise PermissionDenied(
                        detail=messages.UNAUTHORIZED_FILTER_PARAM,
                        code=messages.UNAUTHORIZED_FILTER_PARAM_CODE,
                    )
                filter_kwargs[param] = self.normalize_value(param, value)

        for param, filter_param in self.filter_keys.items():
            if param in request.query_params:
                if not self.has_filter_permission(request, param):
                    raise PermissionDenied(
                        detail=messages.UNAUTHORIZED_FIELD,
                        code=messages.UNAUTHORIZED_FIELD_CODE,
                    )
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
                        filter_kwargs[filter_param] = [
                            self.normalize_value(param, value) for value in values
                        ]
                    else:
                        value = request.query_params[param]
                        if not self.has_filter_permission(request, param, value):
                            raise PermissionDenied(
                                detail=messages.UNAUTHORIZED_FILTER_PARAM,
                                code=messages.UNAUTHORIZED_FILTER_PARAM_CODE,
                            )
                        filter_kwargs[filter_param] = self.normalize_value(param, value)
                elif isinstance(filter_param, Q):
                    filter_args.append(filter_param)
                elif callable(filter_param):
                    try:
                        p = filter_param(request.query_params[param])
                    except (ValueError, TypeError):
                        raise ParseError(
                            detail=messages.MALFORMED_SEARCH_PARAMETER_SPECIFIC % param,
                            code=messages.MALFORMED_SEARCH_PARAMETER_CODE,
                        )
                    filter_args.append(p)
        try:
            queryset = queryset.filter(*filter_args, **filter_kwargs)
        except (ValueError, TypeError):
            raise ParseError(
                detail=messages.MALFORMED_SEARCH_PARAMETER,
                code=messages.MALFORMED_SEARCH_PARAMETER_CODE,
            )

        return queryset

    def normalize_value(self, field, value):
        return value

    def has_filter_permission(self, request, field, value=empty):
        return True


def check_feed(feed, view, query_params):
    if feed is not None:
        # feed makes no sense for detail views or when trying to explicitly filter by state, but for different reasons
        if view.detail:
            raise Http404
        if 'state' in query_params:
            raise ParseError(
                detail=_('Cannot search for state while using the feed endpoint.'),
                code=messages.INVALID_SEARCH_PARAMETER_CODE,
            )


class BidFilter(TrackerFilter):
    filter_keys = {
        'name': 'name__icontains',
        'state': 'state__in',
        'run': 'speedrun__in',
        'parent': 'parent__in',
        'level': 'level',
        'target': 'istarget',
        'trunk': Q(level=0),
        'branch': ~Q(level=0) & Q(istarget=False),
        'leaf': ~Q(level=0) & Q(istarget=True),
        'user_options': lambda n: Q(allowuseroptions=parse_bool(n)),
    }

    def normalize_value(self, field, value):
        if field == 'state':
            return value.upper()
        return value

    def has_filter_permission(self, request, field, value=empty):
        return (
            field != 'state'
            or value is empty
            or value in Bid.PUBLIC_STATES
            or request.user.has_perm('tracker.view_bid')
        )

    def filter_queryset(self, request, queryset, view):
        feed = view.get_feed()
        query_params = request.query_params

        check_feed(feed, view, query_params)

        if view.detail or view.action == ['create']:
            return queryset

        if feed is None:
            if 'state' not in query_params:
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
                if view.action == 'tree':
                    queryset = queryset.filter(options__state='PENDING').distinct()
                else:
                    queryset = queryset.pending()
            # no change for 'all'
        elif feed is not None:
            if feed.lower() in Bid.ALL_FEEDS:
                logger.warning(f'unhandled valid bid feed `{feed}`')
            raise NotFound(
                detail=messages.INVALID_FEED % feed, code=messages.INVALID_FEED_CODE
            )

        if view.action == 'tree':
            for param in ('level', 'trunk', 'branch', 'leaf'):
                if param in query_params:
                    raise ParseError(
                        detail=_('Cannot search for %s while using the tree endpoint.')
                        % param,
                        code=messages.INVALID_SEARCH_PARAMETER_CODE,
                    )

        return super().filter_queryset(request, queryset, view)


class PrizeFilter(TrackerFilter):
    general_filter = ['name', 'description', 'shortdescription']
    filter_lookup = ['event', 'category']
    filter_keys = {
        'name': 'name__icontains',
        'state': 'state__in',
    }

    def normalize_value(self, field, value):
        if field == 'state':
            return value.upper()
        return value

    def has_filter_permission(self, request, field, value=empty):
        return (
            field != 'state'
            or value is empty
            or value in Prize.PUBLIC_STATES
            or request.user.has_perm('tracker.view_prize')
        )

    def filter_queryset(self, request, queryset, view):
        feed = view.get_feed()
        query_params = request.query_params

        check_feed(feed, view, query_params)

        if view.detail or view.action == ['create']:
            return queryset

        if feed is None or feed == 'public':
            if 'state' not in query_params:
                queryset = queryset.public()
        elif feed == 'current':
            if 'run' in request.query_params:
                run = SpeedRunViewSet(
                    kwargs={'pk': request.query_params['run']}, request=request
                ).get_object()
            else:
                run = None
            queryset = queryset.current(
                parse_time(query_params.get('time', None)), run=run
            )
        elif feed == 'all':
            pass  # no change for 'all'
        elif feed is not None:
            if feed.upper() in Prize.ALL_FEEDS:
                logger.warning(f'unhandled valid prize feed `{feed}`')
            raise NotFound(
                detail=messages.INVALID_FEED % feed, code=messages.INVALID_FEED_CODE
            )

        return super().filter_queryset(request, queryset, view)


class TalentFilter(TrackerFilter):
    filter_keys = {
        'name': 'name__icontains',
    }


class DonationFilter(TrackerFilter):
    filter_keys = {
        'amount': 'amount',
        'amount_lte': 'amount__lte',
        'amount_gte': 'amount__gte',
        'time_lte': 'timereceived__lte',
        'time_gte': 'timereceived__gte',
    }
