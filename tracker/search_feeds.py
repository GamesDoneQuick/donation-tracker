import logging
import warnings
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from tracker import util
from tracker.models import Bid, Donation, SpeedRun

_DEFAULT_DONATION_DELTA = timedelta(hours=3)
_DEFAULT_DONATION_MAX = 200
_DEFAULT_DONATION_MIN = 25

# There is a slight complication in how this works, in that we cannot use the 'limit' set-up as a general filter mechanism, so these methods return the actual result, rather than a filter object

logger = logging.getLogger(__name__)


def get_recent_donations(
    donations=None,
    min_donations=_DEFAULT_DONATION_MIN,
    max_donations=_DEFAULT_DONATION_MAX,
    delta=_DEFAULT_DONATION_DELTA,
    query_offset=None,
    **kwargs,
):
    for key, value in kwargs.items():
        if value is not None:
            logger.warning(f'Unexpected param to get_recent_donations: {key}:{value:r}')
    offset = util.parse_time(query_offset)
    if donations is None:
        donations = Donation.objects.all()
    if delta:
        high_filter = donations.filter(timereceived__gte=offset - delta)
    else:
        high_filter = donations
    count = high_filter.count()
    if max_donations is not None and count > max_donations:
        donations = donations[:max_donations]
    elif min_donations is not None and count < min_donations:
        donations = donations[:min_donations]
    else:
        donations = high_filter
    return donations


_DEFAULT_RUN_DELTA = timedelta(hours=6)
_DEFAULT_RUN_MAX = 7
_DEFAULT_RUN_MIN = 3


def get_upcoming_runs(
    runs=None,
    include_current=True,
    max_runs=_DEFAULT_RUN_MAX,
    min_runs=_DEFAULT_RUN_MIN,
    delta=_DEFAULT_RUN_DELTA,
    query_offset=None,
):
    offset = util.parse_time(query_offset)
    if runs is None:
        runs = SpeedRun.objects.all()
    if include_current:
        runs = runs.filter(endtime__gte=offset)
    else:
        runs = runs.filter(starttime__gte=offset)
    if delta:
        high_filter = runs.filter(endtime__lte=offset + delta)
    else:
        high_filter = runs
    count = high_filter.count()
    if max_runs is not None and count > max_runs:
        runs = runs[:max_runs]
    elif min_runs is not None and count < min_runs:
        runs = runs[:min_runs]
    else:
        runs = high_filter
    return runs


def get_future_runs(**kwargs):
    return get_upcoming_runs(include_current=False, **kwargs)


def upcoming_bid_filter(*, query_offset=None, **kwargs):
    query_offset = util.parse_time(query_offset)
    if kwargs:
        warnings.warn(
            f'deprecated to pass args to upcoming_bid_filter: {kwargs}',
            DeprecationWarning,
        )
    return Q(state='OPENED') | Q(
        state__in=Bid.PUBLIC_STATES,
        speedrun__starttime__lte=query_offset,
        speedrun__endtime__gte=query_offset,
    )


def get_upcoming_bids(**kwargs):
    return Bid.objects.filter(upcoming_bid_filter(**kwargs))


def future_bid_filter(**kwargs):
    kwargs.pop('include_current', None)
    return Q(
        speedrun__in=(
            run.id for run in get_upcoming_runs(include_current=False, **kwargs)
        )
    )


# Gets all of the current prizes that are possible right now (and also _specific_ to right now)
def concurrent_prizes_filter(runs):
    run_count = runs.count()
    if run_count == 0:
        return Q(id=None)
    start_time = runs[0].starttime
    end_time = runs.reverse()[0].endtime
    # TODO: with the other changes to the logic I'm not sure this is correct any more, but
    # it's only a rough guess so maybe it's ok - BC 12/2019
    # ----
    # yes, the filter query here is correct.  We want to get all unwon prizes that _start_ before the last run in the list _ends_, and likewise all prizes that _end_ after the first run in the list _starts_.
    return Q(claims=None) & (
        Q(startrun__starttime__lte=end_time, endrun__endtime__gte=start_time)
        | Q(starttime__lte=end_time, endtime__gte=start_time)
        | Q(
            startrun__isnull=True,
            endrun__isnull=True,
            starttime__isnull=True,
            endtime__isnull=True,
        )
    )


def current_prizes_filter(query_offset=None):
    offset = util.parse_time(query_offset)
    return Q(claims=None) & (
        Q(startrun__starttime__lte=offset, endrun__endtime__gte=offset)
        | Q(starttime__lte=offset, endtime__gte=offset)
        | Q(
            startrun__isnull=True,
            endrun__isnull=True,
            starttime__isnull=True,
            endtime__isnull=True,
        )
    )


def upcoming_prizes_filter(**kwargs):
    runs = get_upcoming_runs(**kwargs)
    return concurrent_prizes_filter(runs)


def future_prizes_filter(**kwargs):
    return upcoming_prizes_filter(include_current=False, **kwargs)


def apply_feed_filter(query, model, feed_name, params=None, user=None):
    params = params or {}
    noslice = canonical_bool(params.pop('noslice', False))
    user = user or AnonymousUser()
    if model == 'donation':
        query = donation_feed_filter(feed_name, noslice, params, query, user)
    elif model in ['bid', 'bidtarget', 'allbids']:
        query = bid_feed_filter(feed_name, noslice, params, query, user)
    elif model == 'run':
        query = run_feed_filter(feed_name, noslice, params, query)
    elif model == 'prize':
        query = prize_feed_filter(feed_name, noslice, params, query, user)
    elif model == 'event':
        query = event_feed_filter(feed_name, params, query)
    return query


def event_feed_filter(feed_name, params, query):
    if feed_name == 'future':
        offsettime = util.parse_time(params.get('time', None))
        query = query.filter(datetime__gte=offsettime, archived=False)
    return query


def run_feed_filter(feed_name, noslice, params, query):
    if feed_name == 'current':
        query = get_upcoming_runs(**feed_params(noslice, params, {'runs': query}))
    elif feed_name == 'future':
        query = get_future_runs(**feed_params(noslice, params, {'runs': query}))
    return query


def feed_params(noslice, params, init=None):
    call_params = init or {}
    if 'max_runs' in params:
        call_params['max_runs'] = int(params['max_runs'])
    if 'maxRuns' in params:
        call_params['max_runs'] = int(params['maxRuns'])
    if 'min_runs' in params:
        call_params['min_runs'] = int(params['min_runs'])
    if 'minRuns' in params:
        call_params['min_runs'] = int(params['minRuns'])
    if noslice:
        call_params['max_runs'] = None
        call_params['min_runs'] = None
    if 'delta' in params:
        call_params['delta'] = timedelta(minutes=int(params['delta']))
    if 'time' in params:
        call_params['query_offset'] = util.parse_time(params['time'])
    return call_params


def bid_feed_filter(feed_name, noslice, params, query, user):
    if feed_name == 'all':
        if not user.has_perm('tracker.view_bid'):
            raise PermissionDenied
        pass  # no filtering required
    elif feed_name == 'open':
        query = query.filter(state='OPENED')
    elif feed_name == 'closed':
        query = query.filter(state='CLOSED')
    elif feed_name == 'current':
        query = query.filter(upcoming_bid_filter(**feed_params(noslice, params)))
    elif feed_name == 'future':
        query = query.filter(
            Q(state='OPENED') & future_bid_filter(**feed_params(noslice, params))
        )
    elif feed_name == 'pending':
        if not user.has_perm('tracker.view_bid'):
            raise PermissionDenied
        query = query.filter(state='PENDING', count__gt=0)
    elif feed_name is None:
        query = query.filter(state__in=['OPENED', 'CLOSED'])
    else:
        raise ValueError(f'Unknown feed name `{feed_name}`')
    return query


def donation_feed_filter(feed_name, noslice, params, query, user):
    if (
        feed_name not in ['recent', 'toprocess', 'toread', 'all']
        and feed_name is not None
    ):
        raise ValueError(f'Unknown feed name `{feed_name}`')
    if feed_name == 'recent':
        query = query.recent(
            int(params.get('delta', _DEFAULT_DONATION_DELTA)),
            util.parse_time(params.get('time', None)),
        )
    elif feed_name == 'toprocess':
        if not user.has_perm('tracker.view_comments'):
            raise PermissionDenied
        query = query.to_process()
    elif feed_name == 'toread':
        query = query.to_read()
    if feed_name != 'all':
        query = query.completed()
    elif not user.has_perm('tracker.view_pending_donation'):
        raise PermissionDenied
    return query


def prize_feed_filter(feed_name, noslice, params, query, user):
    if feed_name == 'current':
        call_params = {}
        if 'time' in params:
            call_params['query_offset'] = util.parse_time(params['time'])
        query = query.filter(current_prizes_filter(**call_params))
    elif feed_name == 'future':
        query = query.filter(upcoming_prizes_filter(**feed_params(noslice, params)))
    elif feed_name == 'todraw':
        query = query.to_draw(time=params.get('time', None))
    if feed_name != 'all':
        query = query.filter(state='ACCEPTED')
    elif not user.has_perm('tracker.change_prize'):
        raise PermissionDenied
    return query


def canonical_bool(b):
    if isinstance(b, str):
        if b.lower() in ['t', 'True', 'true', 'y', 'yes']:
            b = True
        elif b.lower() in ['f', 'False', 'false', 'n', 'no']:
            b = False
        else:
            b = None
    return b
