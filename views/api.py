import json
from django.http.response import Http404

from django.contrib.auth.decorators import user_passes_test
from django.db import transaction, connection
from tracker.models import *
import tracker.filters as filters
from tracker.views.common import tracker_response
import tracker.viewutil as viewutil
import tracker.logutil as logutil
from django.http import HttpResponse
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError, PermissionDenied
from django.db.utils import IntegrityError
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
import django.core.serializers as serializers

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
}

permmap = {
    'run'          : 'speedrun'
}
fkmap = { 'winner': 'donor', 'speedrun': 'run', 'startrun': 'run', 'endrun': 'run', 'category': 'prizecategory', 'parent': 'bid'}

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
    del fields[prefix + 'testdonation']
    del fields[prefix + 'domainId']

def prize_privacy_filter(model, fields):
    if model != 'prize':
        return
    del fields['extrainfo']
    del fields['provideremail']

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
            o['fields']['public'] = repr(objs[int(o['pk'])])
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
                o['fields'][r + '__public'] = repr(ro)
            if not authorizedUser:
                donor_privacy_filter(searchtype, o['fields'])
                donation_privacy_filter(searchtype, o['fields'])
                prize_privacy_filter(searchtype, o['fields'])
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

def parse_value(field, value):
    if value == 'None':
        return None
    elif fkmap.get(field,field) in modelmap:
        model = modelmap[fkmap.get(field, field)]
        try:
            value = int(value)
        except ValueError:
            if hasattr(model.objects, 'get_or_create_by_natural_key'):
                return model.objects.get_or_create_by_natural_key(*json.loads(value))[0]
            else:
                return model.objects.get_by_natural_key(*json.loads(value))
        else:
            return model.objects.get(id=int(value))
    return value

def api_v1(request):
    # only here to give a root access point
    raise Http404

@csrf_exempt
@never_cache
def add(request):
    try:
        addParams = viewutil.request_params(request)
        addtype = addParams['type']
        if not request.user.has_perm('tracker.add_' + permmap.get(addtype,addtype)):
            return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
        Model = modelmap[addtype]
        newobj = Model()
        for k,v in addParams.items():
            if k in ('type','id'):
                continue
            setattr(newobj, k, parse_value(k, v))
        newobj.full_clean()
        models = newobj.save() or [newobj]
        logutil.addition(request, newobj)
        resp = HttpResponse(serializers.serialize('json', models, ensure_ascii=False),content_type='application/json;charset=utf-8')
        if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
            return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
        return resp
    except IntegrityError as e:
        return HttpResponse(json.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValidationError as e:
        d = {'error': u'Validation Error'}
        if hasattr(e,'message_dict') and e.message_dict:
            d['fields'] = e.message_dict
        if hasattr(e,'messages') and e.messages:
            d['messages'] = e.messages
        return HttpResponse(json.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except AttributeError as e:
        return HttpResponse(json.dumps({'error': 'Attribute Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except KeyError as e:
        return HttpResponse(json.dumps({'error': 'Key Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except FieldError as e:
        return HttpResponse(json.dumps({'error': 'Field Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValueError as e:
        return HttpResponse(json.dumps({'error': u'Value Error', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ObjectDoesNotExist as e:
        return HttpResponse(json.dumps({'error': 'Foreign Key could not be found', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def delete(request):
    try:
        deleteParams = viewutil.request_params(request)
        deltype = deleteParams['type']
        if not request.user.has_perm('tracker.delete_' + permmap.get(deltype,deltype)):
            return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
        obj = modelmap[deltype].objects.get(pk=deleteParams['id'])
        logutil.deletion(request, obj)
        obj.delete()
        return HttpResponse(json.dumps({'result': u'Object %s of type %s deleted' % (deleteParams['id'], deleteParams['type'])}, ensure_ascii=False), content_type='application/json;charset=utf-8')
    except IntegrityError, e:
        return HttpResponse(json.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValidationError, e:
        d = {'error': u'Validation Error'}
        if hasattr(e,'message_dict') and e.message_dict:
            d['fields'] = e.message_dict
        if hasattr(e,'messages') and e.messages:
            d['messages'] = e.messages
        return HttpResponse(json.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except KeyError, e:
        return HttpResponse(json.dumps({'error': 'Key Error, malformed delete parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ObjectDoesNotExist, e:
        return HttpResponse(json.dumps({'error': 'Object does not exist'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def edit(request):
    try:
        editParams = viewutil.request_params(request)
        edittype = editParams['type']
        if not request.user.has_perm('tracker.change_' + permmap.get(edittype,edittype)):
            return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
        Model = modelmap[edittype]
        obj = Model.objects.get(pk=editParams['id'])
        changed = []
        for k,v in editParams.items():
            if k in ('type','id'):
                continue
            v = parse_value(k, v)
            if unicode(getattr(obj, k)) != unicode(v):
                changed.append(k)
            setattr(obj,k, v)
        obj.full_clean()
        models = obj.save() or [obj]
        if changed:
            logutil.change(request,obj,u'Changed field%s %s.' % (len(changed) > 1 and 's' or '', ', '.join(changed)))
        resp = HttpResponse(serializers.serialize('json', models, ensure_ascii=False),content_type='application/json;charset=utf-8')
        if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
            return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
        return resp
    except IntegrityError as e:
        return HttpResponse(json.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValidationError as e:
        d = {'error': u'Validation Error'}
        if hasattr(e,'message_dict') and e.message_dict:
            d['fields'] = e.message_dict
        if hasattr(e,'messages') and e.messages:
            d['messages'] = e.messages
        return HttpResponse(json.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except AttributeError as e:
        return HttpResponse(json.dumps({'error': 'Attribute Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except KeyError as e:
        return HttpResponse(json.dumps({'error': 'Key Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except FieldError as e:
        return HttpResponse(json.dumps({'error': 'Field Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ValueError as e:
        return HttpResponse(json.dumps({'error': u'Value Error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
    except ObjectDoesNotExist as e:
        return HttpResponse(json.dumps({'error': 'Foreign Key could not be found', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')


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
            status, data = viewutil.draw_prize(prize, seed=requestParams.get('seed',None))
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

@never_cache
@csrf_exempt
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

import commands

@csrf_protect
@never_cache
@transaction.atomic
@user_passes_test(lambda u: u.is_staff)
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
