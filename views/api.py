import json

import collections
import django.core.serializers as serializers
from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import FieldError, FieldDoesNotExist, ObjectDoesNotExist, ValidationError, PermissionDenied
from django.db import transaction, connection
from django.db.utils import IntegrityError
from django.http import HttpResponse
from django.http.response import Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from . import commands
from .. import filters, viewutil, prizeutil, logutil
from ..models import *
from ..views.common import tracker_response

site = admin.site

__all__ = [
    'search',
    'add',
    'edit',
    'delete',
    'command',
    'prize_donors',
    'draw_prize',
    'merge_schedule',
    'refresh_schedule',
    'parse_value',
    'me',
    'api_v1',
]

modelmap = {
    'bid'           : Bid,
    'donationbid'   : DonationBid,
    'donation'      : Donation,
    'donor'         : Donor,
    'event'         : Event,
    'prize'         : Prize,
    'prizecategory' : PrizeCategory,
    'run'           : SpeedRun,
    'prizewinner'   : PrizeWinner,
    'runner'        : Runner,
    'country'       : Country,
}

permmap = {
    'run'          : 'speedrun'
}

related = {
    'bid'          : [ 'speedrun', 'event', 'parent' ],
    'allbids'          : [ 'speedrun', 'event', 'parent' ],
    'bidtarget'          : [ 'speedrun', 'event', 'parent' ],
    'donation'     : [ 'donor' ],
    'prize'        : [ 'category', 'startrun', 'endrun' ],
    'prizewinner'  : [ 'prize', 'winner' ],
}

defer = {
    'bid'    : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'event__date'],
}

def donor_privacy_filter(model, fields):
    visibility = None
    primary = None
    prefix = ''
    if model == 'donor':
        visibility = fields['visibility']
        primary = True
    elif 'donor__visibility' in fields:
        visibility = fields['donor__visibility']
        primary = False
        prefix = 'donor__'
    elif 'winner__visibility' in fields:
        visibility = fields['winner__visibility']
        primary = False
        prefix = 'winner__'
    else:
        return
    for field in list(fields.keys()):
        if field.startswith(prefix + 'address') or field.startswith(prefix + 'runner') or field.startswith(prefix + 'prizecontributor') or 'email' in field:
            del fields[field]
    if visibility == 'FIRST' and fields[prefix + 'lastname']:
        fields[prefix + 'lastname'] = fields[prefix + 'lastname'][0] + "..."
    if (visibility == 'ALIAS' or visibility == 'ANON'):
        fields[prefix + 'lastname'] = None
        fields[prefix + 'firstname'] = None
        fields[prefix + 'public'] = fields[prefix + 'alias']
    if visibility == 'ANON':
        fields[prefix + 'alias'] = None
        fields[prefix + 'public'] = u'(Anonymous)'

def donation_privacy_filter(model, fields):
    primary = None
    if model == 'donation':
        primary = True
    elif 'donation__domainId' in fields:
        primary = False
    else:
        return
    prefix = ''
    if not primary:
        prefix = 'donation__'
    if fields[prefix + 'commentstate'] != 'APPROVED':
        fields[prefix + 'comment'] = None
    del fields[prefix + 'modcomment']
    del fields[prefix + 'fee']
    del fields[prefix + 'requestedalias']
    if prefix + 'requestedemail' in fields:
        del fields[prefix + 'requestedemail']
    del fields[prefix + 'requestedvisibility']
    del fields[prefix + 'requestedsolicitemail']
    del fields[prefix + 'testdonation']
    del fields[prefix + 'domainId']

def prize_privacy_filter(model, fields):
    if model != 'prize':
        return
    del fields['extrainfo']
    del fields['acceptemailsent']
    del fields['state']
    del fields['reviewnotes']

# honestly, I wonder if prizewinner as a whole should not be publicly visible
# REALLY need that whitelist system soon
def prizewinner_privacy_filter(model, fields):
    if model != 'prizewinner':
        return
    del fields['couriername']
    del fields['trackingnumber']
    del fields['shippingstate']
    del fields['shippingcost']
    del fields['winnernotes']
    del fields['shippingnotes']
    del fields['emailsent']
    del fields['acceptemailsentcount']
    del fields['shippingemailsent']
    del fields['auth_code']
    del fields['shipping_receipt_url']

class Filters:
    @staticmethod
    def run(user, fields):
        if not user.has_perm('tracker.can_view_tech_notes'):
            del fields['tech_notes']

@never_cache
def search(request):
    authorizedUser = request.user.has_perm('tracker.can_search')
    #  return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    try:
        searchParams = viewutil.request_params(request)
        searchtype = searchParams['type']
        qs = filters.run_model_query(searchtype, searchParams, user=request.user, mode='admin' if authorizedUser else 'user')
        if searchtype in related:
            qs = qs.select_related(*related[searchtype])
        if searchtype in defer:
            qs = qs.defer(*defer[searchtype])
        qs = qs.annotate(**viewutil.ModelAnnotations.get(searchtype,{}))
        if qs.count() > 1000:
            qs = qs[:1000]
        jsonData = json.loads(serializers.serialize('json', qs, ensure_ascii=False))
        objs = dict(map(lambda o: (o.id,o), qs))
        for o in jsonData:
            baseObj = objs[int(o['pk'])]
            if isinstance(baseObj, Donor):
                o['fields']['public'] = baseObj.visible_name()
            else:
                o['fields']['public'] = unicode(baseObj)
            for a in viewutil.ModelAnnotations.get(searchtype,{}):
                o['fields'][a] = unicode(getattr(objs[int(o['pk'])],a))
            for r in related.get(searchtype,[]):
                ro = objs[int(o['pk'])]
                for f in r.split('__'):
                    if not ro: break
                    ro = getattr(ro,f)
                if not ro: continue
                relatedData = json.loads(serializers.serialize('json', [ro], ensure_ascii=False))[0]
                for f in ro.__dict__:
                    if f[0] == '_' or f.endswith('id') or f in defer.get(searchtype,[]): continue
                    v = relatedData["fields"][f]
                    o['fields'][r + '__' + f] = relatedData["fields"][f]
                if isinstance(ro, Donor):
                    o['fields'][r + '__public'] = ro.visible_name()
                else:
                    o['fields'][r + '__public'] = unicode(ro)
            if not authorizedUser:
                donor_privacy_filter(searchtype, o['fields'])
                donation_privacy_filter(searchtype, o['fields'])
                prize_privacy_filter(searchtype, o['fields'])
            clean_fields = getattr(Filters, searchtype, None)
            if clean_fields:
                clean_fields(request.user, o['fields'])
        resp = HttpResponse(json.dumps(jsonData,ensure_ascii=False),content_type='application/json;charset=utf-8')
        if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
            return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
        return resp
    except KeyError, e:
        return HttpResponse(json.dumps({'error': 'Key Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except FieldError, e:
        return HttpResponse(json.dumps({'error': 'Field Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValidationError, e:
        d = {'error': u'Validation Error'}
        if hasattr(e,'message_dict') and e.message_dict:
            d['fields'] = e.message_dict
        if hasattr(e,'messages') and e.messages:
            d['messages'] = e.messages
        return HttpResponse(json.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')


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
                        'Value for field "%s" could not be parsed as json array for m2m lookup' % (field,))
            else:
                pks = value.split(',')
            try:
                results = list(RelatedModel.objects.filter(pk__in=pks))
            except (ValueError, TypeError): # could not parse pks
                results = [RelatedModel.objects.get_by_natural_key(*to_natural_key(pk)) for pk in pks]
            if len(pks) != len(results):
                bad_pks = set(pks) - set(m.pk for m in results)
                raise RelatedModel.DoesNotExist('Invalid pks: %s' % (bad_pks))
            return results
        else:
            try:
                return RelatedModel.objects.get(pk=value)
            except ValueError: # if pk is not coercable
                def has_add_perm():
                    return user.has_perm('%s.add_%s' % (RelatedModel._meta.app_label, RelatedModel._meta.model_name))
                try:
                    if value[0] in '"[{':
                        key = json.loads(value)
                        if type(key) != list:
                            key = [key]
                    else:
                        key = [value]
                except ValueError:
                    raise ValueError('Value "%s" could not be parsed as json for natural key lookup on field "%s"' % (value, field))
                if hasattr(RelatedModel.objects, 'get_or_create_by_natural_key') and has_add_perm():
                    return RelatedModel.objects.get_or_create_by_natural_key(*key)[0]
                else:
                    return RelatedModel.objects.get_by_natural_key(*key)


def api_v1(request):
    # only here to give a root access point
    raise Http404


def get_admin(Model):
    return admin.site._registry[Model]


def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el


def filter_fields(fields, model_admin, request, obj=None):
    writable_fields = tuple(flatten(model_admin.get_fields(request, obj)))
    readonly_fields = model_admin.get_readonly_fields(request, obj)
    return [field for field in fields if
            (field in writable_fields and field not in readonly_fields)]


def generic_error_json(pretty_error, exception, pretty_exception=None, status=400, additional_keys=()):
    error = {'error': pretty_error, 'exception': pretty_exception or unicode(exception)}
    for key in additional_keys:
        value = getattr(exception, key, None)
        if value:
            error[key] = value
    return HttpResponse(json.dumps(error, ensure_ascii=False), status=status, content_type='application/json;charset=utf-8')


def generic_api_view(view_func):
    def wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except PermissionDenied as e:
            return generic_error_json(u'Permission Denied', e, status=403)
        except IntegrityError as e:
            return generic_error_json(u'Integrity Error', e)
        except ValidationError as e:
            return generic_error_json(u'Validation Error', e,
                                      pretty_exception=u'See message_dict and/or messages for details',
                                      additional_keys=('message_dict', 'messages'))
        except (AttributeError, KeyError, FieldError, ValueError) as e:
            return generic_error_json(u'Malformed Add Parameters', e)
        except FieldDoesNotExist as e:
            return generic_error_json(u'Field does not exist', e)
        except ObjectDoesNotExist as e:
            return generic_error_json(u'Foreign Key relation could not be found', e)
    return wrapped_view


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
def add(request):
    addParams = viewutil.request_params(request)
    addtype = addParams['type']
    Model = modelmap.get(addtype, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % addtype)
    model_admin = get_admin(Model)
    if not model_admin.has_add_permission(request):
        raise PermissionDenied('You do not have permission to add a model of the requested type')
    good_fields = filter_fields(addParams.keys(), model_admin, request)
    bad_fields = set(good_fields) - set(addParams.keys())
    if bad_fields:
        raise PermissionDenied('You do not have permission to set the following field(s) on new objects: %s' %
                               ','.join(sorted(bad_fields)))
    newobj = Model()
    changed_fields = []
    for k,v in addParams.items():
        if k in ('type','id'):
            continue
        new_value = parse_value(Model, k, v, request.user)
        setattr(newobj, k, new_value)
        changed_fields.append('Set %s to "%s".' % (k, new_value))
    newobj.full_clean()
    models = newobj.save() or [newobj]
    logutil.addition(request, newobj)
    logutil.change(request, newobj, ' '.join(changed_fields))
    resp = HttpResponse(serializers.serialize('json', models, ensure_ascii=False),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
def delete(request):
    deleteParams = viewutil.request_params(request)
    deltype = deleteParams['type']
    Model = modelmap.get(deltype, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % deltype)
    obj = Model.objects.get(pk=deleteParams['id'])
    model_admin = get_admin(Model)
    if not model_admin.has_delete_permission(request, obj):
        raise PermissionDenied('You do not have permission to delete that model')
    logutil.deletion(request, obj)
    obj.delete()
    return HttpResponse(json.dumps({'result': u'Object %s of type %s deleted' % (deleteParams['id'], deleteParams['type'])}, ensure_ascii=False), content_type='application/json;charset=utf-8')


@csrf_exempt
@generic_api_view
@never_cache
@transaction.atomic
def edit(request):
    editParams = viewutil.request_params(request)
    edittype = editParams['type']
    Model = modelmap.get(edittype, None)
    if Model is None:
        raise KeyError('%s is not a recognized model type' % edittype)
    Model = modelmap[edittype]
    model_admin = get_admin(Model)
    obj = Model.objects.get(pk=editParams['id'])
    if not model_admin.has_change_permission(request, obj):
        raise PermissionDenied('You do not have permission to change that object')
    good_fields = filter_fields(editParams.keys(), model_admin, request)
    bad_fields = set(good_fields) - set(editParams.keys())
    if bad_fields:
        raise PermissionDenied('You do not have permission to set the following field(s) on the requested object: %s' %
                               ','.join(sorted(bad_fields)))
    changed_fields = []
    for k,v in editParams.items():
        if k in ('type','id'):
            continue
        old_value = getattr(obj, k)
        if hasattr(old_value, 'all'): # accounts for m2m relationships
            old_value = map(unicode, old_value.all())
        new_value = parse_value(Model, k, v, request.user)
        setattr(obj, k, new_value)
        if type(new_value) == list: # accounts for m2m relationships
            new_value = map(unicode, new_value)
        if unicode(old_value) != unicode(new_value):
            if old_value and not new_value:
                changed_fields.append(u'Changed %s from "%s" to empty.' % (k, old_value))
            elif not old_value and new_value:
                changed_fields.append(u'Changed %s from empty to "%s".' % (k, new_value))
            else:
                changed_fields.append(u'Changed %s from "%s" to "%s".' % (k, old_value, new_value))
    obj.full_clean()
    models = obj.save() or [obj]
    if changed_fields:
        logutil.change(request, obj, ' '.join(changed_fields))
    resp = HttpResponse(serializers.serialize('json', models, ensure_ascii=False),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp


@never_cache
def prize_donors(request):
    try:
        if not request.user.has_perm('tracker.change_prize'):
            return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
        requestParams = viewutil.request_params(request)
        id = int(requestParams['id'])
        resp = HttpResponse(json.dumps(Prize.objects.get(pk=id).eligible_donors()),content_type='application/json;charset=utf-8')
        if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
            return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
        return resp
    except Prize.DoesNotExist:
        return HttpResponse(json.dumps({'error': 'Prize id does not exist'}),status=404,content_type='application/json;charset=utf-8')


@csrf_exempt
@never_cache
@transaction.atomic
def draw_prize(request):
    try:
        if not request.user.has_perm('tracker.change_prize'):
            return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')

        requestParams = viewutil.request_params(request)
        id = int(requestParams['id'])
        prize = Prize.objects.get(pk=id)

        if prize.maxed_winners():
            maxWinnersMessage = "Prize: " + prize.name + " already has a winner." if prize.maxwinners == 1 else "Prize: " + prize.name + " already has the maximum number of winners allowed."
            return HttpResponse(json.dumps({'error': maxWinnersMessage}),status=409,content_type='application/json;charset=utf-8')

        skipKeyCheck = requestParams.get('skipkey', False)

        if not skipKeyCheck:
            eligible = prize.eligible_donors()
            if not eligible:
                return HttpResponse(json.dumps({'error': 'Prize has no eligible donors'}),status=409,content_type='application/json;charset=utf-8')
            key = hash(json.dumps(eligible))
            if 'key' not in requestParams:
                return HttpResponse(json.dumps({'key': key}),content_type='application/json;charset=utf-8')
            else:
                try:
                    inputKey = type(key)(requestParams['key'])
                    if inputKey != key:
                        return HttpResponse(json.dumps({'error': 'Key field did not match expected value'},ensure_ascii=False),status=400,content_type='application/json;charset=utf-8')
                except (ValueError,KeyError),e:
                    return HttpResponse(json.dumps({'error': 'Key field was missing or malformed', 'exception': '%s %s' % (type(e),e)},ensure_ascii=False),status=400,content_type='application/json;charset=utf-8')


        if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
            return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')

        limit = requestParams.get('limit', prize.maxwinners)
        if not limit:
            limit = prize.maxwinners

        currentCount = prize.current_win_count()
        status = True
        results = []
        while status and currentCount < limit:
            status, data = prizeutil.draw_prize(prize, seed=requestParams.get('seed',None))
            if status:
                currentCount += 1
                results.append(data)
                logutil.change(request,prize,u'Picked winner. %.2f,%.2f' % (data['sum'],data['result']))
                return HttpResponse(json.dumps({'success': results}, ensure_ascii=False),content_type='application/json;charset=utf-8')
            else:
                return HttpResponse(json.dumps(data),status=400,content_type='application/json;charset=utf-8')
    except Prize.DoesNotExist:
        return HttpResponse(json.dumps({'error': 'Prize id does not exist'}),status=404,content_type='application/json;charset=utf-8')


@never_cache
@transaction.atomic
def merge_schedule(request,id):
    if not request.user.has_perm('tracker.sync_schedule'):
        return tracker_response(request, template='404.html', status=404)
    try:
        event = Event.objects.get(pk=id)
    except Event.DoesNotExist:
        return tracker_response(request, template='tracker/badobject.html', status=404)
    try:
        numRuns = viewutil.merge_schedule_gdoc(event)
    except Exception as e:
        return HttpResponse(json.dumps({'error': e.message }),status=500,content_type='application/json;charset=utf-8')

    return HttpResponse(json.dumps({'result': 'Merged %d run(s)' % numRuns }),content_type='application/json;charset=utf-8')


@csrf_exempt
@never_cache
@transaction.atomic
def refresh_schedule(request):
    from django.contrib.auth.models import User
    try:
        id, username = request.META['HTTP_X_GOOG_CHANNEL_TOKEN'].split(':')
        event = Event.objects.get(id=id)
    except (ValueError, Event.DoesNotExist):
        return HttpResponse(json.dumps({'result': 'Event not found'}), status=404, content_type='application/json;charset=utf-8')
    viewutil.merge_schedule_gdoc(event, username)
    viewutil.tracker_log(u'schedule', u'Merged schedule via push for event {0}'.format(event), event=event,
                         user=User.objects.filter(username=username).first())
    return HttpResponse(json.dumps({'result': 'Merged successfully'}), content_type='application/json;charset=utf-8')


@csrf_protect
@never_cache
@user_passes_test(lambda u: u.is_staff)
@transaction.atomic
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
        return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1), status=status, content_type='application/json;charset=utf-8')
    return resp


@never_cache
def me(request):
    if request.user.is_anonymous() or not request.user.is_active:
        raise PermissionDenied
    output = {
        'username': request.user.username
    }
    if request.user.is_superuser:
        output['superuser'] = True
    if request.user.is_staff:
        output['staff'] = True
    if request.user.user_permissions.exists():
        output['permissions'] = ['%s.%s' % (p.content_type.app_label, p.codename) for p in request.user.user_permissions.all()]
    resp = HttpResponse(json.dumps(output), content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1), status=200, content_type='application/json;charset=utf-8')
    return resp
