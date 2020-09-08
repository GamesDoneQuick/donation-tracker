from datetime import timedelta, datetime

import dateutil.parser
import pytz
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from tracker.models import Donation, SpeedRun, Bid

_DEFAULT_DONATION_DELTA = timedelta(hours=3)
_DEFAULT_DONATION_MAX = 200
_DEFAULT_DONATION_MIN = 25

# There is a slight complication in how this works, in that we cannot use the 'limit' set-up as a general filter mechanism, so these methods return the actual result, rather than a filter object


def get_recent_donations(
    donations=None,
    min_donations=_DEFAULT_DONATION_MIN,
    max_donations=_DEFAULT_DONATION_MAX,
    delta=_DEFAULT_DONATION_DELTA,
    query_offset=None,
):
    offset = default_time(query_offset)
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
    offset = default_time(query_offset)
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


# TODO: why is this so complicated
def upcoming_bid_filter(**kwargs):
    runs = [
        run.id
        for run in get_upcoming_runs(
            SpeedRun.objects.filter(Q(bids__state='OPENED')).distinct(), **kwargs
        )
    ]
    return Q(speedrun__in=runs)


def get_upcoming_bids(**kwargs):
    return Bid.objects.filter(upcoming_bid_filter(**kwargs))


def future_bid_filter(**kwargs):
    return upcoming_bid_filter(include_current=False, **kwargs)


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
    return Q(prizewinner__isnull=True) & (
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
    offset = default_time(query_offset)
    return Q(prizewinner__isnull=True) & (
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


def todraw_prizes_filter(query_offset=None):
    offset = default_time(query_offset)
    return Q(state='ACCEPTED') & (
        Q(prizewinner__isnull=True)
        & (
            Q(endrun__endtime__lte=offset)
            | Q(endtime__lte=offset)
            | (Q(endtime=None) & Q(endrun=None))
        )
    )


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
        offsettime = default_time(params.get('time', None))
        query = query.filter(datetime__gte=offsettime)
    return query


def run_feed_filter(feed_name, noslice, params, query):
    if feed_name == 'current':
        query = get_upcoming_runs(**feed_params(noslice, params, {'runs': query}))
    elif feed_name == 'future':
        query = get_future_runs(**feed_params(noslice, params, {'runs': query}))
    return query


def feed_params(noslice, params, init=None):
    call_params = init or {}
    if 'maxRuns' in params:
        call_params['max_runs'] = int(params['maxRuns'])
    if 'minRuns' in params:
        call_params['min_runs'] = int(params['minRuns'])
    if noslice:
        call_params['max_runs'] = None
        call_params['min_runs'] = None
    if 'delta' in params:
        call_params['delta'] = timedelta(minutes=int(params['delta']))
    if 'time' in params:
        call_params['query_offset'] = default_time(params['time'])
    return call_params


def bid_feed_filter(feed_name, noslice, params, query, user):
    if feed_name == 'all':
        if not user.has_perm('tracker.view_hidden'):
            raise PermissionDenied
        pass  # no filtering required
    elif feed_name == 'open':
        query = query.filter(state='OPENED')
    elif feed_name == 'closed':
        query = query.filter(state='CLOSED')
    elif feed_name == 'current':
        query = query.filter(state='OPENED').filter(
            upcoming_bid_filter(**feed_params(noslice, params))
        )
    elif feed_name == 'future':
        query = query.filter(state='OPENED').filter(
            future_bid_filter(**feed_params(noslice, params))
        )
    elif feed_name == 'pending':
        if not user.has_perm('tracker.view_hidden'):
            raise PermissionDenied
        query = query.filter(state='PENDING')
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
        query = get_recent_donations(
            **feed_params(noslice, params, {'donations': query})
        )
    elif feed_name == 'toprocess':
        if not user.has_perm('tracker.view_comments'):
            raise PermissionDenied
        query = query.filter((Q(commentstate='PENDING') | Q(readstate='PENDING')))
    elif feed_name == 'toread':
        query = query.filter(Q(readstate='READY'))
    if feed_name != 'all':
        query = query.filter(transactionstate='COMPLETED', testdonation=False)
    elif not user.has_perm('tracker.view_pending'):
        raise PermissionDenied
    return query


def prize_feed_filter(feed_name, noslice, params, query, user):
    if feed_name == 'current':
        call_params = {}
        if 'time' in params:
            call_params['query_offset'] = default_time(params['time'])
        query = query.filter(current_prizes_filter(**call_params))
    elif feed_name == 'future':
        query = query.filter(upcoming_prizes_filter(**feed_params(noslice, params)))
    elif feed_name == 'won':
        # TODO: are these used? doesn't seem to take multi-prizes into account
        query = query.filter(Q(prizewinner__isnull=False))
    elif feed_name == 'unwon':
        query = query.filter(Q(prizewinner__isnull=True))
    elif feed_name == 'todraw':
        query = query.filter(todraw_prizes_filter())
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


def default_time(time):
    if time is None:
        time = datetime.now(tz=pytz.utc)
    elif isinstance(time, str):
        time = dateutil.parser.parse(time)
    return time.astimezone(pytz.utc)
