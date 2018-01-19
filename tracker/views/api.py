import collections
import json

import django.core.serializers as serializers
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import (
    FieldError,
    FieldDoesNotExist,
    ObjectDoesNotExist,
    ValidationError,
    PermissionDenied,
)
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction, connection
from django.db.models import (
    Sum,
    Count,
    Max,
    Avg,
    When,
    Case,
    F,
    DecimalField,
    IntegerField,
)
from django.db.models.functions import Coalesce
from django.db.utils import IntegrityError
from django.http import HttpResponse, QueryDict
from django.http.response import Http404
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST, require_GET

from tracker import search_filters, logutil
from tracker.models import (
    Bid,
    Donation,
    DonationBid,
    Donor,
    Event,
    Prize,
    SpeedRun,
    Runner,
    Country,
)
from tracker.search_filters import EventAggregateFilter, PrizeWinnersFilter
from tracker.serializers import TrackerSerializer
from tracker.views import commands

site = admin.site

__all__ = [
    'search',
    'add',
    'edit',
    'delete',
    'command',
    'parse_value',
    'me',
    'root',
]

modelmap = {
    'bid': Bid,
    'bidtarget': Bid,  # TODO: remove this, special filters should not be top level types
    'allbids': Bid,  # TODO: remove this, special filters should not be top level types
    'donationbid': DonationBid,
    'donation': Donation,
    'donor': Donor,
    'event': Event,
    'prize': Prize,
    'run': SpeedRun,
    'runner': Runner,
    'country': Country,
}

permmap = {'run': 'speedrun'}

related = {
    'bid': ['speedrun', 'event', 'parent'],
    'allbids': ['speedrun', 'event', 'parent'],
    'bidtarget': ['speedrun', 'event', 'parent'],
    'donation': ['donor'],
    # 'donationbid' # add some?
    'prize': ['category', 'startrun', 'endrun', 'prev_run', 'next_run'],
}

prefetch = {
    'prize': ['allowed_prize_countries', 'disallowed_prize_regions'],
    'event': ['allowed_prize_countries', 'disallowed_prize_regions'],
    'run': ['runners'],
}

prize_run_fields = ['name', 'starttime', 'endtime', 'display_name', 'order']

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
        'istarget',
        'allowuseroptions',
        'option_max_length',
        'revealedtime',
        'biddependency',
        'total',
        'count',
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
    'donationbid': {'__self__': ['bid', 'donation', 'amount'],},
    'donation': {
        '__self__': [
            'donor',
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
        ],
        'donor': ['alias', 'alias_no', 'visibility'],
    },
    'donor': {
        '__self__': ['alias', 'alias_no', 'firstname', 'lastname', 'visibility'],
    },
    'event': {
        '__self__': [
            'short',
            'name',
            'hashtag',
            'receivername',
            'targetamount',
            'minimumdonation',
            'paypalemail',
            'paypalcurrency',
            'datetime',
            'timezone',
            'locked',
            'allow_donations',
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
        'amount': Coalesce(Sum(EVENT_DONATION_AGGREGATE_FILTER), 0),
        'count': Count(EVENT_DONATION_AGGREGATE_FILTER),
        'max': Coalesce(Max(EVENT_DONATION_AGGREGATE_FILTER), 0),
        'avg': Coalesce(Avg(EVENT_DONATION_AGGREGATE_FILTER), 0),
    },
    'prize': {
        'numwinners': Count(
            Case(When(PrizeWinnersFilter, then=1), output_field=IntegerField())
        ),
    },
}

annotation_coercions = {
    'event': {'amount': float, 'count': int, 'max': float, 'avg': float,},
    'prize': {'numwinners': int,},
}


def donor_privacy_filter(fields):
    visibility = fields['visibility']
    if visibility == 'FIRST' and fields['lastname']:
        fields['lastname'] = fields['lastname'][0] + '...'
    if visibility == 'ALIAS' or visibility == 'ANON':
        del fields['lastname']
        del fields['firstname']
    if visibility == 'ANON':
        del fields['alias']
        del fields['alias_no']
        del fields['canonical_url']


def donation_privacy_filter(fields):
    if fields['commentstate'] != 'APPROVED':
        del fields['comment']
        del fields['commentlanguage']
    if fields['donor__visibility'] == 'ANON':
        del fields['donor']
        del fields['donor__alias']
        del fields['donor__alias_no']
        del fields['donor__visibility']
        del fields['donor__canonical_url']


def run_privacy_filter(fields):
    del fields['tech_notes']


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
        if not request.user.has_perm('tracker.view_usernames'):
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
    limit = getattr(settings, 'TRACKER_PAGINATION_LIMIT', DEFAULT_PAGINATION_LIMIT)
    limit_param = int(single(search_params, 'limit', limit))
    if limit_param > limit:
        raise ValueError('limit can not be above %d' % limit)
    if limit_param < 1:
        raise ValueError('limit must be at least 1')
    limit = min(limit, limit_param)

    qs = search_filters.run_model_query(search_type, search_params, request.user,)

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
        if search_type == 'donor' and not donor_names:
            donor_privacy_filter(obj['fields'])
        elif search_type == 'donation' and not all_comments:
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


def to_natural_key(key):
    return key if type(key) == list else [key]


def parse_value(Model, field, value, user=None):
    user = user or AnonymousUser()
    if value == 'None':
        return None
    else:
        model_field = Model._meta.get_field(field)
        RelatedModel = model_field.related_model
        if RelatedModel is None:
            return value
        if model_field.many_to_many:
            if value[0] == '[':
                try:
                    pks = json.loads(value)
                except ValueError:
                    raise ValueError(
                        'Value for field "%s" could not be parsed as json array for m2m lookup'
                        % (field,)
                    )
            else:
                pks = value.split(',')
            try:
                results = list(RelatedModel.objects.filter(pk__in=pks))
            except (ValueError, TypeError):  # could not parse pks
                results = [
                    RelatedModel.objects.get_by_natural_key(*to_natural_key(pk))
                    for pk in pks
                ]
            if len(pks) != len(results):
                bad_pks = set(pks) - set(m.pk for m in results)
                raise RelatedModel.DoesNotExist('Invalid pks: %s' % (bad_pks))
            return results
        else:
            try:
                return RelatedModel.objects.get(pk=value)
            except ValueError:  # if pk is not coercable

                def has_add_perm():
                    return user.has_perm(
                        '%s.add_%s'
                        % (RelatedModel._meta.app_label, RelatedModel._meta.model_name)
                    )

                try:
                    if value[0] in '"[{':
                        key = json.loads(value)
                        if type(key) != list:
                            key = [key]
                    else:
                        key = [value]
                except ValueError:
                    raise ValueError(
                        'Value "%s" could not be parsed as json for natural key lookup on field "%s"'
                        % (value, field)
                    )
                if (
                    hasattr(RelatedModel.objects, 'get_or_create_by_natural_key')
                    and has_add_perm()
                ):
                    return RelatedModel.objects.get_or_create_by_natural_key(*key)[0]
                else:
                    return RelatedModel.objects.get_by_natural_key(*key)


def root(request):
    # only here to give a root access point
    raise Http404


def get_admin(Model):
    return admin.site._registry[Model]


def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, str):
            for sub in flatten(el):
                yield sub
        else:
            yield el


def filter_fields(fields, model_admin, request, obj=None):
    writable_fields = tuple(flatten(model_admin.get_fields(request, obj)))
    readonly_fields = model_admin.get_readonly_fields(request, obj)
    return [
        field
        for field in fields
        if (field in writable_fields and field not in readonly_fields)
    ]


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
@require_POST
def add(request):
    add_params = request.POST
    add_type = add_params['type']
    Model = modelmap.get(add_type, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % add_type)
    model_admin = get_admin(Model)
    if not model_admin.has_add_permission(request):
        raise PermissionDenied(
            'You do not have permission to add a model of the requested type'
        )
    good_fields = filter_fields(add_params.keys(), model_admin, request)
    bad_fields = set(good_fields) - set(add_params.keys())
    if bad_fields:
        raise PermissionDenied(
            'You do not have permission to set the following field(s) on new objects: %s'
            % ','.join(sorted(bad_fields))
        )
    newobj = Model()
    changed_fields = []
    m2m_collections = []
    for k, v in add_params.items():
        if k in ('type', 'id'):
            continue
        new_value = parse_value(Model, k, v, request.user)
        if type(new_value) == list:  # accounts for m2m relationships
            m2m_collections.append((k, new_value))
            new_value = [str(x) for x in new_value]
        else:
            setattr(newobj, k, new_value)
        changed_fields.append('Set %s to "%s".' % (k, new_value))
    newobj.full_clean()
    models = newobj.save() or [newobj]
    for k, v in m2m_collections:
        getattr(newobj, k).set(v)
    logutil.addition(request, newobj)
    logutil.change(request, newobj, ' '.join(changed_fields))
    resp = HttpResponse(
        serializers.serialize('json', models, ensure_ascii=False),
        content_type='application/json;charset=utf-8',
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    return resp


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
@require_POST
def delete(request):
    delete_params = request.POST
    delete_type = delete_params['type']
    Model = modelmap.get(delete_type, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % delete_type)
    obj = Model.objects.get(pk=delete_params['id'])
    model_admin = get_admin(Model)
    if not model_admin.has_delete_permission(request, obj):
        raise PermissionDenied('You do not have permission to delete that model')
    logutil.deletion(request, obj)
    obj.delete()
    return HttpResponse(
        json.dumps(
            {
                'result': 'Object %s of type %s deleted'
                % (delete_params['id'], delete_params['type'])
            },
            ensure_ascii=False,
        ),
        content_type='application/json;charset=utf-8',
    )


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
@require_POST
def edit(request):
    edit_params = request.POST
    edit_type = edit_params['type']
    Model = modelmap.get(edit_type, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % edit_type)
    Model = modelmap[edit_type]
    model_admin = get_admin(Model)
    obj = Model.objects.get(pk=edit_params['id'])
    if not model_admin.has_change_permission(request, obj):
        raise PermissionDenied('You do not have permission to change that object')
    good_fields = filter_fields(edit_params.keys(), model_admin, request)
    bad_fields = set(good_fields) - set(edit_params.keys())
    if bad_fields:
        raise PermissionDenied(
            'You do not have permission to set the following field(s) on the requested object: %s'
            % ','.join(sorted(bad_fields))
        )
    changed_fields = []
    for k, v in edit_params.items():
        if k in ('type', 'id'):
            continue
        old_value = getattr(obj, k)
        if hasattr(old_value, 'all'):  # accounts for m2m relationships
            old_value = [str(x) for x in old_value.all()]
        new_value = parse_value(Model, k, v, request.user)
        if type(new_value) == list:  # accounts for m2m relationships
            getattr(obj, k).set(new_value)
            new_value = [str(x) for x in new_value]
        else:
            setattr(obj, k, new_value)
        if str(old_value) != str(new_value):
            if old_value and not new_value:
                changed_fields.append('Changed %s from "%s" to empty.' % (k, old_value))
            elif not old_value and new_value:
                changed_fields.append('Changed %s from empty to "%s".' % (k, new_value))
            else:
                changed_fields.append(
                    'Changed %s from "%s" to "%s".' % (k, old_value, new_value)
                )
    obj.full_clean()
    models = obj.save() or [obj]
    if changed_fields:
        logutil.change(request, obj, ' '.join(changed_fields))
    resp = HttpResponse(
        serializers.serialize('json', models, ensure_ascii=False),
        content_type='application/json;charset=utf-8',
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    return resp


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
            output, status = func(data)
            output = serializers.serialize('json', output, ensure_ascii=False)
        else:
            output = json.dumps({'error': 'permission denied'})
            status = 403
    else:
        output = json.dumps({'error': 'unrecognized command'})
        status = 400
    resp = HttpResponse(output, content_type='application/json;charset=utf-8')
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
