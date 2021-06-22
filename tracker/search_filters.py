from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from tracker.models import (
    Bid,
    Donation,
    DonationBid,
    Donor,
    DonorCache,
    DonorPrizeEntry,
    Event,
    Milestone,
    Prize,
    PrizeWinner,
    Runner,
    SpeedRun,
)
from tracker.search_feeds import canonical_bool, apply_feed_filter

# FIXME: why is there more than one of these
_ModelMap = {
    # TODO: different kinds of bids should be a parameter, not a top level type
    'allbids': Bid,
    'bid': Bid,
    'bidtarget': Bid,
    'donationbid': DonationBid,
    'donation': Donation,
    'donor': Donor,
    'donorcache': DonorCache,
    'event': Event,
    'milestone': Milestone,
    'prize': Prize,
    'prizewinner': PrizeWinner,
    'prizeentry': DonorPrizeEntry,
    'run': SpeedRun,
    'runner': Runner,
}

_ModelDefaultQuery = {
    'bidtarget': Q(allowuseroptions=True) | Q(options__isnull=True, istarget=True),
    'bid': Q(level=0),
    'donor': ~Q(visibility='ANON'),
    'milestone': Q(visible=True),
}

_ModelReverseMap = {v: k for k, v in _ModelMap.items()}

_GeneralFields = {
    # There was a really weird bug when doing the full recursion on speedrun, where it would double-select the related bids in aggregate queries
    # it seems to be related to selecting the donor table as part of the 'runners' recurse thing
    # it only applied to challenges too for some reason.  I can't figure it out, and I don't really want to waste more time on it, so I'm just hard-coding it to do the specific speedrun fields only
    'bid': ['event', 'speedrun', 'name', 'description', 'shortdescription'],
    'allbids': [
        'event',
        'speedrun',
        'name',
        'description',
        'shortdescription',
        'parent',
    ],
    'bidtarget': [
        'event',
        'speedrun',
        'name',
        'description',
        'shortdescription',
        'parent',
    ],
    'bidsuggestion': ['name', 'bid'],
    'donationbid': ['donation', 'bid'],
    'donation': ['donor', 'comment', 'modcomment'],
    'donor': ['email', 'alias', 'firstname', 'lastname', 'paypalemail'],
    'event': ['short', 'name'],
    'prize': ['name', 'description', 'shortdescription'],
    'run': ['name', 'description'],
    'runner': ['name', 'stream', 'twitter', 'youtube', 'platform', 'pronouns'],
}

BID_FIELDS = {
    'event': 'event',
    'eventshort': 'event__short__iexact',
    'eventname': 'event__name__icontains',
    'locked': 'event__locked',
    'run': 'speedrun',
    'runname': 'speedrun__name__icontains',
    'parent': 'parent',
    'parentname': 'parent__name__icontains',
    'name': 'name__icontains',
    'description': 'description__icontains',
    'shortdescription': 'shortdescription__icontains',
    'state': 'state__iexact',
    'revealedtime_gte': 'revealedtime__gte',
    'revealedtime_lte': 'revealedtime__lte',
    'istarget': 'istarget',
    'allowuseroptions': 'allowuseroptions',
    'total_gte': 'total__gte',
    'total_lte': 'total__lte',
    'count_gte': 'count__gte',
    'count_lte': 'count__lte',
    'count': 'count',
}

# Some of these fields are used internally by the code or the `lookups` endpoints
_SpecificFields = {
    'bid': BID_FIELDS,
    'allbids': BID_FIELDS,
    'bidtarget': BID_FIELDS,
    'donationbid': {
        'event': 'donation__event',
        'eventshort': 'donation__event__short__iexact',
        'eventname': 'donation__event__name__icontains',
        'locked': 'donation__event__locked',
        'run': 'bid__speedrun',
        'runname': 'bid__speedrun__name__icontains',
        'bid': 'bid',
        'bidname': 'bid__name__icontains',
        'donation': 'donation',
        'donor': 'donation__donor',
        'amount': 'amount',
        'amount_lte': 'amount__lte',
        'amount_gte': 'amount__gte',
    },
    'donation': {
        'event': 'event',
        'eventshort': 'event__short__iexact',
        'eventname': 'event__name__icontains',
        'locked': 'event__locked',
        'donor': lambda key: Q(donor=key) & ~Q(donor__visibility='ANON'),
        'domain': 'domain',
        'transactionstate': 'transactionstate',
        'bidstate': 'bidstate',
        'commentstate': 'commentstate',
        'readstate': 'readstate',
        'amount': 'amount',
        'amount_lte': 'amount__lte',
        'amount_gte': 'amount__gte',
        'time_lte': 'timereceived__lte',
        'time_gte': 'timereceived__gte',
        'comment': 'comment__icontains',
        'modcomment': 'modcomment__icontains',
    },
    'donor': {
        'event': 'donation__event',
        'eventshort': 'donation__event__short__iexact',
        'eventname': 'donation__event__name__icontains',
        'firstname': 'firstname__icontains',
        'lastname': 'lastname__icontains',
        'alias': 'alias__icontains',
        'email': 'email__icontains',
        'visibility': 'visibility__iexact',
    },
    'donorcache': {
        'event': 'event',
        'firstname': 'donor__firstname__icontains',
        'lastname': 'donor__lastname__icontains',
        'alias': 'donor__alias__icontains',
        'email': 'donor__email__icontains',
        'visibility': 'donor__visibility__iexact',
    },
    'event': {
        'name': 'name__icontains',
        'short': 'short__iexact',
        'locked': 'locked',
        'datetime_lte': 'datetime__lte',
        'datetime_gte': 'datetime__gte',
    },
    'milestone': {'event': 'event',},
    'prize': {
        'event': 'event',
        'eventname': 'event__name__icontains',
        'eventshort': 'event__short__iexact',
        'locked': 'event__locked',
        'category': 'category',
        'categoryname': 'category__name__icontains',
        'name': 'name__icontains',
        'startrun': 'startrun',
        'endrun': 'endrun',
        'starttime_lte': ['starttime__lte', 'startrun__starttime__lte'],
        'starttime_gte': ['starttime__gte', 'startrun__starttime__gte'],
        'endtime_lte': ['endtime__lte', 'endrun__endtime__lte'],
        'endtime_gte': ['endtime__gte', 'endrun__endtime__gte'],
        'description': 'description__icontains',
        'shortdescription': 'shortdescription__icontains',
        'sumdonations': 'sumdonations',
        'randomdraw': 'randomdraw',
        'provider': 'provider__icontains',
        'handler': 'handler',
        'creator': 'creator',
    },
    'prizewinner': {
        'event': 'prize__event',
        'eventname': 'prize__event__name__icontains',
        'eventshort': 'prize__event__short__iexact',
        'prizename': 'prize__name__icontains',
        'prize': 'prize',
        'emailsent': 'emailsent',
        'winner': 'winner',
        'locked': 'prize__event__locked',
    },
    'prizeentry': {
        'donor': 'donor',
        'prize': 'prize',
        'prizename': 'prize__name__icontains',
        'event': 'prize__event',
        'eventname': 'prize__event__name__icontains',
        'eventshort': 'prize__event__short__iexact',
        'weight': 'weight',
        'weight_lte': 'weight__lte',
        'weight_gte': 'weight__gte',
        'locked': 'prize__event__locked',
    },
    'run': {
        'event': 'event',
        'eventname': 'event__name__icontains',
        'eventshort': 'event__short__iexact',
        'locked': 'event__locked',
        'name': 'name__icontains',
        'runner': 'runners',
        'runnername': 'runners__name__icontains',
        'description': 'description__icontains',
        'starttime_lte': 'starttime__lte',
        'starttime_gte': 'starttime__gte',
        'endtime_lte': 'endtime__lte',
        'endtime_gte': 'endtime__gte',
    },
    'runner': {
        'name': 'name__iexact',
        'stream': 'stream',
        'twitter': 'twitter',
        'youtube': 'youtube',
        'event': 'speedrun__event',
    },
}

_FKMap = {
    'winner': 'donor',
    'speedrun': 'run',
    'startrun': 'run',
    'endrun': 'run',
    'option': 'bid',
    'runners': 'donor',
    'parent': 'bid',
}

_DonorEmailFields = ['email', 'paypalemail']
_DonorNameFields = ['firstname', 'lastname', 'alias']
_SpecialMarkers = ['icontains', 'contains', 'iexact', 'exact', 'lte', 'gte']


def single(query_dict, key, *fallback):
    if key not in query_dict:
        if len(fallback):
            return fallback[0]
        else:
            raise KeyError('Missing parameter: %s' % key)
    value = query_dict.pop(key)
    if type(value) != list:
        return value
    if len(value) != 1:
        raise KeyError('Parameter repeated: %s' % key)
    return value[0]


# additional considerations for permission related visibility at the 'field' level


def check_field_permissions(rootmodel, key, value, user=None):
    user = user or AnonymousUser()
    toks = key.split('__')
    if len(toks) >= 2:
        tail = toks[-2]
        rootmodel = _FKMap.get(tail, tail)
    field = toks[-1]
    # cannot search for locked=True unless you can view locked events
    if (
        field == 'locked'
        and canonical_bool(value)
        and not user.has_perm('tracker.view_locked_events')
    ):
        raise PermissionDenied
    if rootmodel == 'donor':
        if (field in _DonorEmailFields) and not user.has_perm('tracker.view_emails'):
            raise PermissionDenied
        elif (field in _DonorNameFields) and not user.has_perm(
            'tracker.view_usernames'
        ):
            raise PermissionDenied
    elif rootmodel == 'donation':
        if (field == 'testdonation') and not user.has_perm('tracker.view_test'):
            raise PermissionDenied
        if (field == 'comment') and not user.has_perm('tracker.view_comments'):
            raise PermissionDenied
    elif rootmodel in ['bid', 'allbids', 'bidtarget']:
        if (
            (field == 'state')
            and not user.has_perm('tracker.view_hidden_bid')
            and value not in ['OPENED', 'CLOSED']
        ):
            raise PermissionDenied


def recurse_keys(key, from_models=None):
    from_models = from_models or []
    tail = key.split('__')[-1]
    ftail = _FKMap.get(tail, tail)
    if ftail in _GeneralFields:
        ret = []
        for key in _GeneralFields[ftail]:
            if key not in from_models:
                from_models.append(key)
                for k in recurse_keys(key, from_models):
                    ret.append(tail + '__' + k)
            return ret
    return [key]


def build_general_query_piece(rootmodel, key, text, user):
    if text:
        # These can throw if somebody is trying to access, say, the lookups endpoints without being logged in
        check_field_permissions(rootmodel, key, text, user)
        return Q(**{key + '__icontains': text})
    return Q()


def normalize_model_param(model):
    if model == 'speedrun':
        model = 'run'  # we should really just rename all instances of it already!
    if model not in _ModelMap:
        model = _ModelReverseMap[model]
    return model


def model_general_filter(model, text, user):
    fields = set()
    model = normalize_model_param(model)
    from_models = [model]
    if model not in _GeneralFields:
        raise KeyError("Requested model does not support the 'q' parameter")
    for key in _GeneralFields[model]:
        fields |= set(recurse_keys(key, from_models=from_models))
    fields = list(fields)
    query = Q()
    for field in fields:
        query |= build_general_query_piece(model, field, text, user)
    return query


def model_specific_filter(model, params, user):
    query = Q()
    model = normalize_model_param(model)
    specifics = _SpecificFields[model]
    keys = list(params.keys())
    filters = {k: single(params, k) for k in keys if k in specifics}
    if params:  # anything leftover is unrecognized
        raise KeyError("Invalid search parameters: '%s'" % ','.join(params.keys()))
    for param, value in filters.items():
        check_field_permissions(model, param, value, user)
        specific = specifics[param]
        field_query = Q()
        if isinstance(specific, str) or not hasattr(specific, '__iter__'):
            specific = [specific]
        for search_key in specific:
            if isinstance(search_key, str):
                field_query |= Q(**{search_key: value})
            else:
                field_query |= search_key(value)
        query &= field_query
    return query


def run_model_query(model, params, user=None):
    user = user or AnonymousUser()
    params = params.copy() if params else {}
    model = normalize_model_param(model)

    filtered = _ModelMap[model].objects.all()

    filter_accumulator = Q()

    if model in _ModelDefaultQuery:
        filter_accumulator &= _ModelDefaultQuery[model]

    pk = single(params, 'id', None)
    pks = single(params, 'ids', None)
    # technically speaking it's a viable query but why would you do this
    if pk and pks:
        raise KeyError('Cannot combine `id` with `ids` query')
    if pk:
        filter_accumulator &= Q(pk=pk)
    if pks:
        filter_accumulator &= Q(pk__in=pks.split(','))

    # arguably does not make sense if combined with id or ids, but I can think of some use cases, so just let it go for now
    q = params.pop('q', None)
    if q:
        filter_accumulator &= model_general_filter(model, q, user)

    feed = single(params, 'feed', None)
    feed_params = {
        k: single(params, k)
        for k in [
            'noslice',
            'delta',
            'time',
            'maxDonations',
            'minDonations',
            'maxRuns',
            'minRuns',
        ]
        if k in params
    }

    filter_accumulator &= model_specific_filter(model, params, user)
    filtered = filtered.filter(filter_accumulator)

    if model in ['bid', 'bidtarget', 'allbids']:
        filtered = filtered.order_by(*Bid._meta.ordering)

    filtered = apply_feed_filter(filtered, model, feed, feed_params, user)

    if 'maxRuns' in feed_params or 'minRuns' in feed_params:
        return filtered  # stupid hack

    return filtered.distinct()


_1ToManyDonationAggregateFilter = Q(donation__transactionstate='COMPLETED')
DonationBidAggregateFilter = _1ToManyDonationAggregateFilter
DonorAggregateFilter = _1ToManyDonationAggregateFilter
EventAggregateFilter = _1ToManyDonationAggregateFilter
PrizeWinnersFilter = Q(prizewinner__acceptcount__gt=0) | Q(
    prizewinner__pendingcount__gt=0
)
_1ToManyBidsAggregateFilter = Q(bids__donation__transactionstate='COMPLETED')
