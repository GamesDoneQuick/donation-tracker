import json

from django.contrib import admin
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.core import serializers
from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    F,
    FloatField,
    IntegerField,
    Max,
    Sum,
    When,
)
from django.db.models.functions import Cast, Coalesce
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponse, QueryDict
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from tracker import search_filters, settings
from tracker.models import (
    Ad,
    Bid,
    Country,
    Donation,
    DonationBid,
    Event,
    Interview,
    Milestone,
    Prize,
    SpeedRun,
    Tag,
    Talent,
)
from tracker.search_filters import EventAggregateFilter, PrizeWinnersFilter
from tracker.serializers import TrackerSerializer
from tracker.views import commands

site = admin.site

__all__ = [
    'search',
    'gone',
    'command',
    'me',
    'root',
    'ads',
    'interviews',
]

modelmap = {
    'bid': Bid,
    'bidtarget': Bid,  # TODO: remove this, special filters should not be top level types
    'allbids': Bid,  # TODO: remove this, special filters should not be top level types
    'donationbid': DonationBid,
    'donation': Donation,
    'headset': Talent,
    'milestone': Milestone,
    'event': Event,
    'prize': Prize,
    'run': SpeedRun,
    'runner': Talent,
    'country': Country,
    'tag': Tag,
}

related = {
    'run': ['priority_tag'],
    'bid': ['speedrun', 'event', 'parent', 'parent__speedrun', 'parent__event'],
    'allbids': ['speedrun', 'event', 'parent', 'parent__speedrun', 'parent__event'],
    'bidtarget': ['speedrun', 'event', 'parent', 'parent__speedrun', 'parent__event'],
    'prize': ['category', 'startrun', 'endrun', 'prev_run', 'next_run'],
}

prefetch = {
    'prize': ['allowed_prize_countries', 'disallowed_prize_regions', 'tags'],
    'event': ['allowed_prize_countries', 'disallowed_prize_regions'],
    'run': ['runners', 'hosts', 'commentators', 'tags'],
}

prize_run_fields = ['name', 'starttime', 'endtime', 'display_name', 'order', 'category']

bid_fields = {
    '__self__': [
        'event',
        'speedrun',
        'parent',
        'name',
        'state',
        'description',
        'shortdescription',
        'goal',
        'repeat',
        'istarget',
        'allowuseroptions',
        'option_max_length',
        'revealedtime',
        'biddependency',
        'total',
        'count',
        'pinned',
    ],
    'speedrun': [
        'name',
        'display_name',
        'twitch_name',
        'order',
        'starttime',
        'endtime',
        'public',
    ],
    'event': ['short', 'name', 'timezone', 'datetime'],
    'parent': [
        'name',
        'state',
        'goal',
        'allowuseroptions',
        'option_max_length',
        'total',
        'count',
    ],
}

included_fields = {
    'bid': bid_fields,
    'bidtarget': bid_fields,
    'allbids': bid_fields,
    'donationbid': {
        '__self__': ['bid', 'donation', 'amount'],
    },
    'donation': {
        '__self__': [
            'event',
            'domain',
            'transactionstate',
            'readstate',
            'commentstate',
            'amount',
            'currency',
            'timereceived',
            'comment',
            'commentlanguage',
            'pinned',
        ],
    },
    'event': {
        '__self__': [
            'short',
            'name',
            'hashtag',
            'receivername',
            'receiver_short',
            'targetamount',
            'minimumdonation',
            'paypalemail',
            'paypalcurrency',
            'datetime',
            'timezone',
            'locked',
            'allow_donations',
            'use_one_step_screening',
        ],
    },
    'prize': {
        '__self__': [
            'name',
            'category',
            'image',
            'altimage',
            'imagefile',
            'description',
            'shortdescription',
            'estimatedvalue',
            'minimumbid',
            'maximumbid',
            'sumdonations',
            'randomdraw',
            'event',
            'startrun',
            'endrun',
            'starttime',
            'endtime',
            'maxwinners',
            'maxmultiwin',
            'provider',
            'creator',
            'creatoremail',
            'creatorwebsite',
            'custom_country_filter',
            'key_code',
        ],
        'startrun': prize_run_fields,
        'endrun': prize_run_fields,
        'category': ['name'],
    },
}

EVENT_DONATION_AGGREGATE_FILTER = Case(
    When(EventAggregateFilter, then=F('donation__amount')),
    output_field=DecimalField(decimal_places=2),
)

annotations = {
    'event': {
        'amount': Cast(
            Coalesce(Sum(EVENT_DONATION_AGGREGATE_FILTER), 0.0),
            output_field=FloatField(),
        ),
        'count': Count(EVENT_DONATION_AGGREGATE_FILTER),
        'max': Cast(
            Coalesce(Max(EVENT_DONATION_AGGREGATE_FILTER), 0.0),
            output_field=FloatField(),
        ),
        'avg': Cast(
            Coalesce(Avg(EVENT_DONATION_AGGREGATE_FILTER), 0.0),
            output_field=FloatField(),
        ),
    },
    'prize': {
        'numwinners': Count(
            Case(When(PrizeWinnersFilter, then=1), output_field=IntegerField())
        ),
    },
}

annotation_coercions = {
    'event': {
        'amount': float,
        'count': int,
        'max': float,
        'avg': float,
    },
    'prize': {
        'numwinners': int,
    },
}


def donation_privacy_filter(fields):
    if fields['commentstate'] != 'APPROVED':
        del fields['comment']
        del fields['commentlanguage']


def run_privacy_filter(fields):
    del fields['tech_notes']
    del fields['layout']


def generic_error_json(
    pretty_error, exception, pretty_exception=None, status=400, additional_keys=()
):
    error = {'error': pretty_error, 'exception': pretty_exception or str(exception)}
    for key in additional_keys:
        value = getattr(exception, key, None)
        if value is not None:
            error[key] = value
    return HttpResponse(
        json.dumps(error, ensure_ascii=False),
        status=status,
        content_type='application/json;charset=utf-8',
    )


def generic_api_view(view_func):
    def wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except PermissionDenied as e:
            return generic_error_json('Permission Denied', e, status=403)
        except IntegrityError as e:
            return generic_error_json('Integrity Error', e)
        except ValidationError as e:
            return generic_error_json(
                'Validation Error',
                e,
                pretty_exception='See message_dict and/or messages for details',
                additional_keys=('message_dict', 'messages', 'code', 'params'),
            )
        except (AttributeError, KeyError, FieldError, ValueError) as e:
            return generic_error_json('Malformed Parameters', e)
        except FieldDoesNotExist as e:
            return generic_error_json('Field does not exist', e)
        except ObjectDoesNotExist as e:
            return generic_error_json('Foreign Key relation could not be found', e)

    return wrapped_view


def single(query_dict, key, *fallback):
    if key not in query_dict:
        if len(fallback):
            return fallback[0]
        else:
            raise KeyError('Missing parameter: %s' % key)
    value = query_dict.pop(key)
    if len(value) != 1:
        raise KeyError('Parameter repeated: %s' % key)
    return value[0]


def present(query_dict, key):
    if key not in query_dict:
        return False
    value = single(query_dict, key)
    if value != '':
        raise ValueError(f'"{key}" parameter does not take a value')
    return True


DEFAULT_PAGINATION_LIMIT = 500


@generic_api_view
@require_GET
@cache_page(0)
def search(request):
    search_params = QueryDict.copy(request.GET)
    search_type = single(search_params, 'type')
    queries = present(search_params, 'queries')
    donor_names = present(search_params, 'donor_names')
    all_comments = present(search_params, 'all_comments')
    tech_notes = present(search_params, 'tech_notes')
    Model = modelmap.get(search_type, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % search_type)
    if queries and not request.user.has_perm('tracker.view_queries'):
        raise PermissionDenied
    # TODO: move these to a lookup table?
    if donor_names:
        if search_type != 'donor':
            raise KeyError('"donor_names" can only be applied to donor searches')
        if not request.user.has_perm('tracker.view_full_names'):
            raise PermissionDenied
    if all_comments:
        if search_type != 'donation':
            raise KeyError('"all_comments" can only be applied to donation searches')
        if not request.user.has_perm('tracker.view_comments'):
            raise PermissionDenied
    if tech_notes:
        if search_type != 'run':
            raise KeyError('"tech_notes" can only be applied to run searches')
        if not request.user.has_perm('tracker.can_view_tech_notes'):
            raise PermissionDenied

    offset = int(single(search_params, 'offset', 0))
    if offset < 0:
        raise ValueError('offset must be at least 0')
    limit = settings.TRACKER_PAGINATION_LIMIT
    limit_param = int(single(search_params, 'limit', limit))
    if limit_param > limit:
        raise ValueError(f'limit can not be above {limit}')
    if limit_param < 1:
        raise ValueError('limit must be at least 1')
    limit = min(limit, limit_param)

    qs = search_filters.run_model_query(
        search_type,
        search_params,
        request.user,
    )

    qs = qs[offset : (offset + limit)]

    # Django 3.1 doesn't like Model.Meta.ordering when combined with annotations, so this guarantees the
    # correct subset when using annotations, even if it does result in an extra query
    if search_type in annotations:
        qs = (
            Model.objects.filter(pk__in=(m.pk for m in qs))
            .annotate(**annotations[search_type])
            .order_by()
        )
    if search_type in related:
        qs = qs.select_related(*related[search_type])
    if search_type in prefetch:
        qs = qs.prefetch_related(*prefetch[search_type])

    include_fields = included_fields.get(search_type, {})

    result = TrackerSerializer(Model, request).serialize(
        qs, fields=include_fields.get('__self__', None)
    )
    objs = {o.id: o for o in qs}

    related_cache = {}

    for obj in result:
        base_obj = objs[int(obj['pk'])]
        if hasattr(base_obj, 'visible_name'):
            obj['fields']['public'] = base_obj.visible_name()
        else:
            obj['fields']['public'] = str(base_obj)
        for a in annotations.get(search_type, {}):
            func = annotation_coercions.get(search_type, {}).get(a, str)
            obj['fields'][a] = func(getattr(base_obj, a))
        for prefetched_field in prefetch.get(search_type, []):
            if '__' in prefetched_field:
                continue
            obj['fields'][prefetched_field] = [
                po.id for po in getattr(base_obj, prefetched_field).all()
            ]
        for related_field in related.get(search_type, []):
            related_object = base_obj
            for field in related_field.split('__'):
                if not related_object:
                    break
                if not related_object._meta.get_field(field).serialize:
                    related_object = None
                else:
                    related_object = getattr(related_object, field)
            if not related_object:
                continue
            if related_object not in related_cache:
                related_cache[related_object] = (
                    TrackerSerializer(type(related_object), request).serialize(
                        [related_object], fields=include_fields.get(related_field, None)
                    )
                )[0]
            related_data = related_cache[related_object]
            for field, values in related_data['fields'].items():
                if field.endswith('id'):
                    continue
                obj['fields'][related_field + '__' + field] = values
            if hasattr(related_object, 'visible_name'):
                obj['fields'][
                    related_field + '__public'
                ] = related_object.visible_name()
            else:
                obj['fields'][related_field + '__public'] = str(related_object)
        if search_type == 'donation' and not all_comments:
            donation_privacy_filter(obj['fields'])
        elif search_type == 'run' and not tech_notes:
            run_privacy_filter(obj['fields'])
    resp = HttpResponse(
        json.dumps(result, ensure_ascii=False, cls=DjangoJSONEncoder),
        content_type='application/json;charset=utf-8',
    )
    if queries:
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    # TODO: cache control for certain kinds of searches
    return resp


def root(request):
    # only here to give a root access point
    raise Http404


def gone(request, *args, **kwargs):
    return HttpResponse(status=410)


@csrf_protect
@never_cache
@user_passes_test(lambda u: u.is_staff)
@transaction.atomic
@require_POST
def command(request):
    data = json.loads(request.POST.get('data', '{}'))
    func = getattr(commands, data['command'], None)
    if func:
        if request.user.has_perm(func.permission):
            output, status = func({k: v for k, v in data.items() if k != 'command'})
            if status == 200:
                output = serializers.serialize('json', output, ensure_ascii=False)
            else:
                output = json.dumps(output)
        else:
            output = json.dumps({'error': 'permission denied'})
            status = 403
    else:
        output = json.dumps({'error': 'unrecognized command'})
        status = 400
    resp = HttpResponse(
        output, status=status, content_type='application/json;charset=utf-8'
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            status=status,
            content_type='application/json;charset=utf-8',
        )
    return resp


@generic_api_view
@never_cache
@require_GET
def me(request):
    if request.user.is_anonymous or not request.user.is_active:
        raise PermissionDenied
    output = {'username': request.user.username}
    if request.user.is_superuser:
        output['superuser'] = True
    else:
        permissions = request.user.get_all_permissions()
        if permissions:
            output['permissions'] = list(permissions)
    if request.user.is_staff:
        output['staff'] = True
    resp = HttpResponse(
        json.dumps(output), content_type='application/json;charset=utf-8'
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            status=200,
            content_type='application/json;charset=utf-8',
        )
    return resp


def _interstitial_info(serialized, models, Model):
    for model in serialized:
        real = next(m for m in models if m.pk == model['pk'])
        model['fields'].update(
            {
                'anchor': real.anchor_id,
                'order': real.order,
                'suborder': real.suborder,
                'event_id': real.event_id,
                'length': real.length,
                'tags': [t.name for t in real.tags.all()],
            }
        )
    return serialized


@generic_api_view
@never_cache
@permission_required('tracker.view_ad', raise_exception=True)
@require_GET
def ads(request, event):
    models = Ad.objects.filter(event=event).prefetch_related('tags')
    resp = HttpResponse(
        json.dumps(
            _interstitial_info(
                json.loads(serializers.serialize('json', models, ensure_ascii=False)),
                models,
                Ad,
            )
        ),
        content_type='application/json;charset=utf-8',
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    return resp


@generic_api_view
@never_cache
@require_GET
def interviews(request, event):
    models = Interview.objects.filter(event=event).prefetch_related('tags')
    if 'all' in request.GET:
        if not request.user.has_perm('tracker.view_interview'):
            raise PermissionDenied
    else:
        models = models.public()
    resp = HttpResponse(
        json.dumps(
            _interstitial_info(
                json.loads(serializers.serialize('json', models, ensure_ascii=False)),
                models,
                Interview,
            )
        ),
        content_type='application/json;charset=utf-8',
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    return resp
