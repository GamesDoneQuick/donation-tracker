import django

from django import shortcuts
from django.shortcuts import render,render_to_response

from django.db import connection
from django.db.models import Count,Sum,Max,Avg,Q
from django.db.utils import ConnectionDoesNotExist,IntegrityError

from django.core import serializers,paginator
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.exceptions import FieldError,ObjectDoesNotExist
from django.core.urlresolvers import reverse

from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm

from django.http import HttpResponse,HttpResponseRedirect
from django.http import Http404

from django import template
from django.template import RequestContext
from django.template.base import TemplateSyntaxError

from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect,csrf_exempt
from django.views.decorators.http import require_POST

from django.utils import translation
import simplejson; #TODO: tell someone to install the latest simplejson on the server

from paypal.standard.forms import PayPalPaymentsForm;
from paypal.standard.ipn.models import PayPalIPN;
from paypal.standard.ipn.forms import PayPalIPNForm;

from tracker.models import *
from tracker.forms import *
import tracker.filters as filters;

import tracker.viewutil as viewutil
import tracker.paypalutil as paypalutil

from django.core.serializers.json import DjangoJSONEncoder

import gdata.spreadsheet.service
import gdata.spreadsheet.text_db

import sys
import datetime
import settings
import logutil as log
import pytz
import random
import decimal
import re
import dateutil.parser;
import itertools;

def dv():
  return str(django.VERSION[0]) + '.' + str(django.VERSION[1]) + '.' + str(django.VERSION[2])

def pv():
  return str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])

def fixorder(queryset, orderdict, sort, order):
  queryset = queryset.order_by(*orderdict[sort])
  if order == -1:
    queryset = queryset.reverse()
  return queryset
  
@csrf_protect
@never_cache
def login(request):
  redirect_to = request.REQUEST.get('next', '/')
  if len(redirect_to) == 0 or redirect_to[0] != '/':
    redirect_to = '/' + redirect_to
  while redirect_to[:2] == '//':
    redirect_to = '/' + redirect_to[2:]
  if request.method == 'POST':
    form = AuthenticationForm(data=request.POST)
    if form.is_valid():
      auth_login(request, form.get_user())
  return django.shortcuts.redirect(redirect_to)

@never_cache
def logout(request):
  auth_logout(request)
  return django.shortcuts.redirect(request.META.get('HTTP_REFERER', '/'))

def tracker_response(request=None, template='tracker/index.html', qdict={}, status=200):
  starttime = datetime.datetime.now()
  context = RequestContext(request)
  language = translation.get_language_from_request(request)
  translation.activate(language)
  request.LANGUAGE_CODE = translation.get_language()
  profile = None
  if request.user.is_authenticated():
    try:
      profile = request.user.get_profile()
    except UserProfile.DoesNotExist:
      profile = UserProfile()
      profile.user = request.user
      profile.save()
  if profile:
    template = profile.prepend + template
    prepend = profile.prepend
  else:
    prepend = ''
  authform = AuthenticationForm(request.POST)
  qdict.update({
    'djangoversion' : dv(),
    'pythonversion' : pv(),
    'user' : request.user,
    'profile' : profile,
    'prepend' : prepend,
    'next' : request.REQUEST.get('next', request.path),
    'starttime' : starttime,
    'authform' : authform })
  qdict.setdefault('event',viewutil.get_event(None))
  try:
    if request.user.username[:10]=='openiduser':
      qdict.setdefault('usernameform', UsernameForm())
      return render(request, 'tracker/username.html', dictionary=qdict)
    resp = render(request, template, dictionary=qdict, status=status)
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1, use_decimal=True),content_type='application/json;charset=utf-8')
    return resp
  except Exception,e:
    if request.user.is_staff and not settings.DEBUG:
      return HttpResponse(unicode(type(e)) + '\n\n' + unicode(e), mimetype='text/plain', status=500)
    raise

def eventlist(request):
  return tracker_response(request, 'tracker/eventlist.html', { 'events' : Event.objects.all() })

def index(request,event=None):
  event = viewutil.get_event(event)
  eventParams = {}
  if event.id:
    eventParams['event'] = event.id;
  agg = filters.run_model_query('donation', eventParams, user=request.user, mode='user').aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
  agg['target'] = event.targetamount;
  count = {
    'runs' : filters.run_model_query('run', eventParams, user=request.user).count(),
    'prizes' : filters.run_model_query('prize', eventParams, user=request.user).count(),
    'challenges' : filters.run_model_query('challenge', eventParams, user=request.user).count(),
    'choices' : filters.run_model_query('choice', eventParams, user=request.user).count(),
    'donors' : filters.run_model_query('donor', eventParams, user=request.user).filter(viewutil.DonorAggregateFilter).count(),
  }
  if 'json' in request.GET:
    return HttpResponse(simplejson.dumps({'count':count,'agg':agg},ensure_ascii=False,cls=DjangoJSONEncoder),content_type='application/json;charset=utf-8')
  return tracker_response(request, 'tracker/index.html', { 'agg' : agg, 'count' : count, 'event': event })

@never_cache
def setusername(request):
  if not request.user.is_authenticated or request.user.username[:10]!='openiduser' or request.method != 'POST':
    return django.shortcuts.redirect(reverse('tracker.views.index'))
  usernameform = UsernameForm(request.POST)
  if usernameform.is_valid():
    request.user.username = request.POST['username']
    request.user.save()
    return shortcuts.redirect(request.POST['next'])
  return tracker_response(request, template='tracker/username.html', qdict={ 'usernameform' : usernameform })

modelmap = {
  'challenge'     : Challenge,
  'challengebid'  : ChallengeBid,
  'choice'        : Choice,
  'choicebid'     : ChoiceBid,
  'choiceoption'  : ChoiceOption,
  'donation'      : Donation,
  'donor'         : Donor,
  'event'         : Event,
  'prize'         : Prize,
  'prizecategory' : PrizeCategory,
  'run'           : SpeedRun,
  }
permmap = {
  'run'          : 'speedrun'
  }
fkmap = { 'winner': 'donor', 'speedrun': 'run', 'startrun': 'run', 'endrun': 'run', 'option': 'choiceoption', 'category': 'prizecategory' }

related = {
  'challenge'    : [ 'speedrun' ],
  'choice'       : [ 'speedrun' ],
  'choiceoption' : [ 'choice', 'choice__speedrun' ],
  'donation'     : [ 'donor' ],
  'prize'        : [ 'category', 'startrun', 'endrun', 'winner' ],
};

defer = {
  'challenge'    : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
  'choice'       : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
  'choiceoption' : [ 'choice__speedrun__description', 'choice__speedrun__endtime', 'choice__speedrun__starttime', 'choice__speedrun__runners', 'choice__speedrun__sortkey', 'choice__description', 'choice__pin', 'choice__state', ],
}

@never_cache
def search(request):
  if not request.user.has_perm('tracker.can_search'):
    return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
  try:
    searchtype = request.GET['type']
    qs = filters.run_model_query(searchtype, request.GET, user=request.user, mode='admin');
    if searchtype in related:
      qs = qs.select_related(*related[searchtype])
    if searchtype in defer:
      qs = qs.defer(*defer[searchtype])
    qs = qs.annotate(**viewutil.ModelAnnotations.get(searchtype,{}))
    json = simplejson.loads(serializers.serialize('json', qs, ensure_ascii=False))
    objs = dict(map(lambda o: (o.id,o), qs))
    for o in json:
      for a in viewutil.ModelAnnotations.get(searchtype,{}):
        o['fields'][a] = unicode(getattr(objs[int(o['pk'])],a))
      for r in related.get(searchtype,[]):
        ro = objs[int(o['pk'])]
        for f in r.split('__'):
          if not ro: break
          ro = getattr(ro,f)
        if not ro: continue
        for f in ro.__dict__:
          if f[0] == '_' or f.endswith('id') or f in defer.get(searchtype,[]): continue
          v = unicode(getattr(ro,f))
          o['fields'][r + '__' + f] = v
    resp = HttpResponse(simplejson.dumps(json,ensure_ascii=False),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
  except KeyError, e:
    return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except FieldError, e:
    return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValidationError, e:
    d = {'error': u'Validation Error'}
    if hasattr(e,'message_dict') and e.message_dict:
      d['fields'] = e.message_dict
    if hasattr(e,'messages') and e.messages:
      d['messages'] = e.messages
    return HttpResponse(simplejson.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def add(request):
  try:
    addtype = request.POST['type']
    if not request.user.has_perm('tracker.add_' + permmap.get(addtype,addtype)):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    Model = modelmap[addtype]
    newobj = Model()
    for k,v in request.POST.items():
      if k in ('type','id'):
        continue;
      if v == 'None':
        v = None
      elif fkmap.get(k,k) in modelmap:
        v = modelmap[fkmap.get(k,k)].objects.get(id=v)
      setattr(newobj,k,v)
    newobj.full_clean()
    newobj.save()
    log.addition(request, newobj)
    resp = HttpResponse(serializers.serialize('json', Model.objects.filter(id=newobj.id), ensure_ascii=False),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
  except IntegrityError, e:
    return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValidationError, e:
    d = {'error': u'Validation Error'}
    if hasattr(e,'message_dict') and e.message_dict:
      d['fields'] = e.message_dict
    if hasattr(e,'messages') and e.messages:
      d['messages'] = e.messages
    return HttpResponse(simplejson.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except KeyError, e:
    return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except FieldError, e:
    return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValueError, e:
    return HttpResponse(simplejson.dumps({'error': u'Value Error', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def delete(request):
  try:
    deltype = request.POST['type']
    if not request.user.has_perm('tracker.delete_' + permmap.get(deltype,deltype)):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    obj = modelmap[deltype].objects.get(pk=request.POST['id'])
    log.deletion(request, obj)
    obj.delete()
    return HttpResponse(simplejson.dumps({'result': u'Object %s of type %s deleted' % (request.POST['id'],request.POST['type'])}, ensure_ascii=False), content_type='application/json;charset=utf-8')
  except IntegrityError, e:
    return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValidationError, e:
    d = {'error': u'Validation Error'}
    if hasattr(e,'message_dict') and e.message_dict:
      d['fields'] = e.message_dict
    if hasattr(e,'messages') and e.messages:
      d['messages'] = e.messages
    return HttpResponse(simplejson.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except KeyError, e:
    return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed delete parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ObjectDoesNotExist, e:
    return HttpResponse(simplejson.dumps({'error': 'Object does not exist'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def edit(request):
  try:
    edittype = request.POST['type']
    if not request.user.has_perm('tracker.change_' + permmap.get(edittype,edittype)):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    Model = modelmap[edittype]
    obj = Model.objects.get(pk=request.POST['id'])
    changed = []
    for k,v in request.POST.items():
      if k in ('type','id'): continue
      if v == 'None':
        v = None
      elif fkmap.get(k,k) in modelmap:
        v = modelmap[fkmap.get(k,k)].objects.get(id=v)
      if unicode(getattr(obj,k)) != unicode(v):
        changed.append(k)
      setattr(obj,k,v)
    obj.full_clean()
    obj.save()
    if changed:
      log.change(request,obj,u'Changed field%s %s.' % (len(changed) > 1 and 's' or '', ', '.join(changed)))
    resp = HttpResponse(serializers.serialize('json', Model.objects.filter(id=obj.id), ensure_ascii=False),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
  except IntegrityError, e:
    return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValidationError, e:
    d = {'error': u'Validation Error'}
    if hasattr(e,'message_dict') and e.message_dict:
      d['fields'] = e.message_dict
    if hasattr(e,'messages') and e.messages:
      d['messages'] = e.messages
    return HttpResponse(simplejson.dumps(d, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except KeyError, e:
    return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except FieldError, e:
    return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValueError, e:
    return HttpResponse(simplejson.dumps({'error': u'Value Error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

def challengeindex(request,event=None):
  event = viewutil.get_event(event)
  searchForm = BidSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid filter form', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;
  challenges = filters.run_model_query('challenge', searchParams, user=request.user);
  agg = challenges.aggregate(**viewutil.ModelAnnotations['challenge'])
  challenges = challenges.select_related('speedrun').annotate(**viewutil.ModelAnnotations['challenge'])
  return tracker_response(request, 'tracker/challengeindex.html', { 'searchForm': searchForm, 'challenges' : challenges, 'agg' : agg, 'event' : event })

def challenge(request,id):
  try:
    orderdict = {
      'name'   : ('donation__donor__lastname', 'donation__donor__firstname'),
      'amount' : ('amount', ),
      'time'   : ('donation__timereceived', ),
    }
    sort = request.GET.get('sort', 'time')
    if sort not in orderdict:
      sort = 'time'
    try:
      order = int(request.GET.get('order', '-1'))
    except ValueError:
      order = -1
    challenge = Challenge.objects.get(pk=id)
    event = challenge.speedrun.event;
    bids = ChallengeBid.objects.filter(challenge__exact=id).filter(viewutil.ChallengeBidAggregateFilter);
    agg = bids.aggregate(amount=Sum('amount'), count=Count('amount'))
    bids = bids.select_related('donation','donation__donor').order_by('-donation__timereceived')
    bids = fixorder(bids, orderdict, sort, order)
    comments = 'comments' in request.GET

    return tracker_response(request, 'tracker/challenge.html', { 'event': event, 'challenge' : challenge, 'comments' : comments, 'bids' : bids, 'agg' : agg })
  except Challenge.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def choiceindex(request,event=None):
  event = viewutil.get_event(event)
  searchForm = BidSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;

  """
  choices = filters.run_model_query('choice', searchParams, user=request.user);
  choices = choices.select_related('speedrun','speedrun__event').prefetch_related('option');
  choices = choices.extra(select={'optionid': 'tracker_choiceoption.id'})
  agg = choices.aggregate(**viewutil.ModelAnnotations['choice'])
  choices = choices.annotate(**viewutil.ModelAnnotations['choice']).order_by('speedrun__event__date','speedrun__sortkey','name')
  
  # This is really kludgy, but I couldn't figure out any other reasonable way to annotate the related fields properly :(
  result = [];
  lastChoice = None;
  for choice in choices:
    if not lastChoice or lastChoice.id != choice.id:
      lastChoice = choice;
      result.append(lastChoice);
    for option in lastChoice.option.all():
      if option.id == choice.optionid:
        print("Optionid: " + str(option.id) + " " + str(choice.optionid));
        option.amount = choice.amount;
        option.count = choice.count;
  """
   
  choices = filters.run_model_query('choice', searchParams, user=request.user);
  agg = choices.aggregate(**viewutil.ModelAnnotations['choice']);
  choices = choices.extra(select={'optionid': 'tracker_choiceoption.id', 'optionname': 'tracker_choiceoption.name'}).annotate(**viewutil.ModelAnnotations['choice']).order_by('speedrun__sortkey','name','-amount','option__name')
  
  
  return tracker_response(request, 'tracker/choiceindex.html', { 'searchForm': searchForm, 'choices' : choices, 'agg' : agg, 'event' : event })

def choice(request,id):
  try:
    choice = Choice.objects.get(pk=id)
    event = choice.speedrun.event;
    options = ChoiceOption.objects.filter(choice=id).annotate(**viewutil.ModelAnnotations['choiceoption']).order_by('-amount')
    choicebids = ChoiceBid.objects.filter(option__choice=id).filter(viewutil.ChoiceBidAggregateFilter).select_related('option', 'donation', 'donation__donor').order_by('-donation__timereceived')
    agg = choicebids.aggregate(amount=Sum('amount'), count=Count('amount'))
    comments = 'comments' in request.GET
    return tracker_response(request, 'tracker/choice.html', { 'event': event, 'choice' : choice, 'choicebids' : choicebids, 'comments' : comments, 'options' : options, 'agg' : agg })
  except Choice.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def choiceoption(request,id):
  try:
    orderdict = {
      'name'   : ('donation__donor__lastname', 'donation__donor__firstname'),
      'amount' : ('amount', ),
      'time'   : ('donation__timereceived', ),
    }
    sort = request.GET.get('sort', 'time')
    if sort not in orderdict:
      sort = 'time'
    try:
      order = int(request.GET.get('order', '-1'))
    except ValueError:
      order = -1
    choiceoption = ChoiceOption.objects.get(pk=id)
    event = choiceoption.choice.speedrun.event;
    bids = choiceoption.bids.filter(viewutil.ChoiceBidAggregateFilter)
    agg = bids.filter(option=id).aggregate(amount=Sum('amount'))
    bids = bids.select_related('donation','donation__donor')
    bids = fixorder(bids, orderdict, sort, order)
    comments = 'comments' in request.GET
    return tracker_response(request, 'tracker/choiceoption.html', { 'event': event, 'choiceoption' : choiceoption, 'bids' : bids, 'comments' : comments, 'agg' : agg })
  except ChoiceOption.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

@never_cache
def donorindex(request,event=None):
  event = viewutil.get_event(event)
  orderdict = {
    'name'  : ('lastname', 'firstname'),
    'total' : ('amount',   ),
    'max'   : ('max',      ),
    'avg'   : ('avg',      )
  }
  page = request.GET.get('page', 1)
  sort = request.GET.get('sort', 'name')
  if sort not in orderdict:
    sort = 'name'
  try:
    order = int(request.GET.get('order', 1))
  except ValueError:
    order = 1

  searchForm = DonorSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;
    
  donors = filters.run_model_query('donor', searchParams, user=request.user);
  
  selectionRestriction = Q(donation__transactionstate='COMPLETED');
  
  if event.id:
    selectionRestriction &= Q(donation__event=event);

  donors = donors.annotate(**viewutil.ModelAnnotations['donor']);
  
  # TODO: fix caching to work with the expanded parameters (basically, anything a 'normal' user would search by should be cacheable)
  # We should actually probably fix/abstract this to general caching on all entities while we're at it
  #lasttime = Donation.objects.reverse()
  #if event.id:
  #  lasttime = lasttime.filter(event=event) 
  #try:
  #  cached = None
  #  lasttime = lasttime[0].timereceived
  #  cachekey = u'lasttime:%s:%s' % (event.id,lasttime)
  #  cached = cache.get(cachekey)
  #except IndexError: # no donations
  #  cachekey = u'nodonations'
  #if cached:
  #  donors = cached
  #else:
  #  donors = donors.filter(lastname__isnull=False)
  #  if event.id:
  #    donors = donors.extra(select={
  #      'amount': 'SELECT SUM(amount) FROM tracker_donation WHERE tracker_donation.donor_id = tracker_donor.id AND tracker_donation.event_id = %d' % event.id,
  #      'count' : 'SELECT COUNT(*) FROM tracker_donation WHERE tracker_donation.donor_id = tracker_donor.id AND tracker_donation.event_id = %d' % event.id,
  #      'max' : 'SELECT MAX(amount) FROM tracker_donation WHERE tracker_donation.donor_id = tracker_donor.id AND tracker_donation.event_id = %d' % event.id,
  #      'avg' : 'SELECT AVG(amount) FROM tracker_donation WHERE tracker_donation.donor_id = tracker_donor.id AND tracker_donation.event_id = %d' % event.id,
  #      })
  #  else:
  #    donors = donors.annotate(amount=Sum('donation__amount'), count=Count('donation__amount'), max=Max('donation__amount'), avg=Avg('donation__amount'))
  #  cache.set(cachekey,donors,1800)
  
  donors = donors.order_by(*orderdict[sort])
  if order < 0:
    donors = donors.reverse()
  donors = filter(lambda d: d.count > 0, donors)
  fulllist = request.user.has_perm('tracker.view_full_list') and page == 'full'
  pages = Paginator(donors,50)
  if fulllist:
    pageinfo = { 'paginator' : pages, 'has_previous' : False, 'has_next' : False, 'paginator.num_pages' : pages.num_pages }
    page = 0
  else:
    try:
      pageinfo = pages.page(page)
    except paginator.PageNotAnInteger:
      pageinfo = pages.page(1)
    except paginator.EmptyPage:
      pageinfo = pages.page(pages.num_pages)
      page = pages.num_pages
    donors = pageinfo.object_list
  return tracker_response(request, 'tracker/donorindex.html', { 'searchForm': searchForm, 'donors' : donors, 'event' : event, 'pageinfo' : pageinfo, 'page' : page, 'fulllist' : fulllist, 'sort' : sort, 'order' : order })

def donor(request,id,event=None):
  try:
    event = viewutil.get_event(event)
    donor = Donor.objects.get(pk=id)
    donations = donor.donation_set.filter(transactionstate='COMPLETED');
    if event.id:
      donations = donations.filter(event=event)
    comments = 'comments' in request.GET
    agg = donations.aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
    return tracker_response(request, 'tracker/donor.html', { 'donor' : donor, 'donations' : donations, 'agg' : agg, 'comments' : comments, 'event' : event })
  except Donor.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def donationindex(request,event=None):
  event = viewutil.get_event(event)
  orderdict = {
    'name'   : ('donor__lastname', 'donor__firstname'),
    'amount' : ('amount', ),
    'time'   : ('timereceived', ),
  }
  page = request.GET.get('page', 1)
  sort = request.GET.get('sort', 'time')
  if sort not in orderdict:
    sort = 'time'
  try:
    order = int(request.GET.get('order', -1))
  except ValueError:
    order = -1;
  searchForm = DonationSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;
  donations = filters.run_model_query('donation', searchParams, user=request.user);
  if order < 0:
    donations = donations.reverse()
  fulllist = request.user.has_perm('tracker.view_full_list') and page == 'full'
  pages = Paginator(donations,50)
  if fulllist:
    pageinfo = { 'paginator' : pages, 'has_previous' : False, 'has_next' : False, 'paginator.num_pages' : pages.num_pages }
    page = 0
  else:
    try:
      pageinfo = pages.page(page)
    except paginator.PageNotAnInteger:
      pageinfo = pages.page(1)
    except paginator.EmptyPage:
      pageinfo = pages.page(paginator.num_pages)
      page = pages.num_pages
    donations = pageinfo.object_list
  agg = donations.aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
  return tracker_response(request, 'tracker/donationindex.html', { 'searchForm': searchForm, 'donations' : donations, 'pageinfo' :  pageinfo, 'page' : page, 'fulllist' : fulllist, 'agg' : agg, 'sort' : sort, 'order' : order, 'event': event })

def donation(request,id):
  try:
    donation = Donation.objects.get(pk=id)
    event = donation.event;
    donor = donation.donor
    choicebids = ChoiceBid.objects.filter(donation=id).select_related('option','option__choice','option__choice__speedrun')
    challengebids = ChallengeBid.objects.filter(donation=id).select_related('challenge', 'challenge__speedrun')
    return tracker_response(request, 'tracker/donation.html', { 'event': event, 'donation' : donation, 'donor' : donor, 'choicebids' : choicebids, 'challengebids' : challengebids })
  except Donation.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def runindex(request,event=None):
  event = viewutil.get_event(event);
  searchForm = RunSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;
  runs = filters.run_model_query('run', searchParams, user=request.user);
  runs = runs.select_related('runners').annotate(choices=Sum('choice'), challenges=Sum('challenge'))
  return tracker_response(request, 'tracker/runindex.html', { 'searchForm': searchForm, 'runs' : runs, 'event': event })

def run(request,id):
  try:
    run = SpeedRun.objects.get(pk=id)
    runners = run.runners.all();
    event = run.event;
    challenges = filters.run_model_query('challenge', {'speedrun': id}, user=request.user).annotate(**viewutil.ModelAnnotations['challenge'])
    choices = filters.run_model_query('choice', {'speedrun': id}, user=request.user).extra(select={'optionid': 'tracker_choiceoption.id', 'optionname': 'tracker_choiceoption.name'}).annotate(**viewutil.ModelAnnotations['choice']).order_by('speedrun__sortkey','name','-amount','option__name')
    return tracker_response(request, 'tracker/run.html', { 'event': event, 'run' : run, 'runners': runners, 'challenges' : challenges, 'choices' : choices })
  except SpeedRun.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def prizeindex(request,event=None):
  event = viewutil.get_event(event)
  searchForm = PrizeSearchForm(request.GET);
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400);
  searchParams = {};
  searchParams.update(request.GET);
  searchParams.update(searchForm.cleaned_data);
  if event.id:
    searchParams['event'] = event.id;
  prizes = filters.run_model_query('prize', searchParams, user=request.user);
  prizes = prizes.select_related('startrun','endrun','winner','category')
  return tracker_response(request, 'tracker/prizeindex.html', { 'searchForm': searchForm, 'prizes' : prizes })

def prize(request,id):
  try:
    prize = Prize.objects.get(pk=id)
    event = prize.event;
    games = None
    winner = None
    contributors = prize.contributors.all();
    if prize.startrun:
      games = SpeedRun.objects.filter(sortkey__gte=SpeedRun.objects.get(pk=prize.startrun.id).sortkey,sortkey__lte=SpeedRun.objects.get(pk=prize.endrun.id).sortkey)
    if prize.winner:
      winner = Donor.objects.get(pk=prize.winner.id)
    if prize.category:
      category = PrizeCategory.objects.get(pk=prize.category.id)
    return tracker_response(request, 'tracker/prize.html', { 'event': event, 'prize' : prize, 'games' : games, 'winner' : winner, 'category': category, 'contributors': contributors })
  except Prize.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

@never_cache
def prize_donors(request,id):
  try:
    if not request.user.has_perm('tracker.change_prize'):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    resp = HttpResponse(simplejson.dumps(Prize.objects.get(pk=id).eligibledonors(),use_decimal=True),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1,use_decimal=True),content_type='application/json;charset=utf-8')
    return resp
  except Prize.DoesNotExist:
    return HttpResponse(simplejson.dumps({'error': 'Prize id does not exist'},use_decimal=True),status=404,content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
def draw_prize(request,id):
  try:
    if not request.user.has_perm('tracker.change_prize'):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    prize = Prize.objects.get(pk=id)
    eligible = prize.eligibledonors()
    key = hash(simplejson.dumps(eligible,use_decimal=True));
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1, use_decimal=True),content_type='application/json;charset=utf-8')
    if prize.winner:
      return HttpResponse(simplejson.dumps({'error': 'Prize already has a winner', 'winner': prize.winner.id},ensure_ascii=False),status=400,content_type='application/json;charset=utf-8')
    if not eligible:
      return HttpResponse(simplejson.dumps({'error': 'Prize has no eligible donors'}, use_decimal=True),status=409,content_type='application/json;charset=utf-8')
    if request.method == 'GET':
      return HttpResponse(simplejson.dumps({'key': key}, use_decimal=True),content_type='application/json;charset=utf-8')
    elif request.method == 'POST':
      try:
        okey = int(request.POST['key'])
      except (ValueError,KeyError),e:
        return HttpResponse(simplejson.dumps({'error': 'Key field was missing or malformed', 'exception': '%s %s' % (type(e),e)},ensure_ascii=False, use_decimal=True),status=400,content_type='application/json;charset=utf-8')
      if key != okey:
        return HttpResponse(simplejson.dumps({'error': 'Key field did not match expected value', 'expected': key}, use_decimal=True),status=400,content_type='application/json;charset=utf-8')
      try:
        random.seed(request.POST.get('seed',None))
      except TypeError: # not sure how this could happen but hey
        return HttpResponse(simplejson.dumps({'error': 'Seed parameter was unhashable'}, use_decimal=True),status=400,content_type='application/json;charset=utf-8')
      psum = reduce(lambda a,b: a+b['weight'], eligible, 0.0)
      result = random.random() * psum
      ret = {'sum': psum, 'result': result}
      for d in eligible:
        if result < d['weight']:
          prize.winner = Donor.objects.get(pk=d['donor'])
          prize.emailsent = False;
          break
        result -= d['weight']
      ret['winner'] = prize.winner.id
      log.change(request,prize,u'Picked winner. %.2f,%.2f' % (psum,result))
      prize.save()
      return HttpResponse(simplejson.dumps(ret, ensure_ascii=False, use_decimal=True),content_type='application/json;charset=utf-8')
  except Prize.DoesNotExist:
    return HttpResponse(simplejson.dumps({'error': 'Prize id does not exist'}, use_decimal=True),status=404,content_type='application/json;charset=utf-8')

@never_cache
def merge_schedule(request,id):
  if not request.user.has_perm('tracker.sync_schedule'):
    return tracker_response(request, template='404.html', status=404)
  try:
    event = Event.objects.get(pk=id)
  except Event.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

  LIST_FEED_URL_FORMAT = "https://spreadsheets.google.com/feeds/list/%s/1/private/basic"
  # This is required by the gdoc api to identify the name of the application making the request, but it can basically be any string
  PROGRAM_NAME = "sda-webtracker"

  def find_people(people_list):
    result = [];
    for person in people_list:
        try:
          d = Donor.objects.get(alias__iequals=person);
          result.append(d);
        except:
          pass;
    return result;
    
  class MarathonSpreadSheetEntry:
    def __init__(self, name, time, estimate, runners=[], commentators=[], comments=''):
      self.gamename = name.lower()
      self.starttime = time
      self.endtime = estimate
      self.runners = find_people(runners);
      self.commentators = find_people(commentators);
      self.comments = comments or ''
    def __unicode__(self):
      return self.gamename
    def __repr__(self):
      return u"MarathonSpreadSheetEntry('%s','%s','%s','%s','%s','%s')" % (self.starttime,
        self.gamename, self.runners, self.endtime, self.commentators, self.comments)

  def ParseSpreadSheetEntry(row):
    estimatedTimeDelta = datetime.timedelta()
    postGameSetup = datetime.timedelta()
    rowEntries = gdata.spreadsheet.text_db.Record(row_entry=row).content
    comments = '';
    commentators = '';
    startTime = dateutil.parser.parse(rowEntries[event.scheduledatetimefield]);
    gameName = rowEntries[event.schedulegamefield]
    runners = viewutil.natural_list_parse(rowEntries[event.schedulerunnersfield])
    if rowEntries[event.scheduleestimatefield]:
      toks = rowEntries[event.scheduleestimatefield].split(":")
      if len(toks) == 3:
        estimatedTimeDelta = datetime.timedelta(hours=int(toks[0]), minutes=int(toks[1]), seconds=int(toks[2]))
    # I'm not sure what should be done with the post-game set-up field...
    if event.schedulesetupfield:
      if rowEntries[event.schedulesetupfield]:
        toks = rowEntries[event.schedulesetupfield].split(":")
        if len(toks) == 3:
          postGameSetup = datetime.timedelta(hours=int(toks[0]), minutes=int(toks[1]), seconds=int(toks[2]))
    if event.schedulecommentatorsfield:
      commentators = viewutil.natural_list_parse(rowEntries[event.schedulecommentatorsfield]);
    if event.scehdulecommentsfield:
      comments = rowEntries[event.schedulecommentsfield]
    estimatedTime = startTime + estimatedTimeDelta
    # Convert the times into UTC
    timezone = pytz.timezone(event.scheduletimezone);
    startTime = timezone.localize(startTime)
    estimatedTime = timezone.localize(estimatedTime)
    ret = MarathonSpreadSheetEntry(gameName, startTime, estimatedTime+postGameSetup, runners, commentators, comments);
    return ret
  spreadsheetService = gdata.spreadsheet.service.SpreadsheetsService()
  spreadsheetService.ClientLogin(settings.GDOC_USERNAME, settings.GDOC_PASSWORD)
  listFeed = spreadsheetService.GetListFeed(key=event.scheduleid)
  try:
    runs = filter(lambda r: 'setup' not in r.gamename.lower() and 'end' not in r.gamename.lower(), map(ParseSpreadSheetEntry, listFeed.entry))
  except KeyError:
    return HttpResponse(simplejson.dumps({'error': 'KeyError, make sure the column names are correct'}),status=500,content_type='application/json;charset=utf-8')
  existingruns = dict(map(lambda r: (r.name.lower(),r),SpeedRun.objects.filter(event=event)))
  sortkey = 0
  for run in runs:
    r = existingruns.get(run.gamename,SpeedRun(name=run.gamename,event=event,description=run.comments))
    r.sortkey = sortkey
    for runner in run.runners:
      r.runners.add(runner);
    r.starttime = run.starttime
    r.endtime = run.endtime
    r.save()
    sortkey += 1
  def prizecmp(a,b):
    # if both prizes are run-linked, sort them that way
    if a.startrun and b.startrun:
      return cmp(a.startrun.starttime,b.startrun.starttime) or cmp(a.endrun.endtime,b.endrun.endtime) or cmp(a.name,b.name)
    # else if they're both time-linked, sort them that way
    if a.starttime and b.starttime:
      return cmp(a.starttime,b.starttime) or cmp(a.endtime,b.endtime) or cmp(a.name,b.name)
    # run-linked prizes are listed after time-linked and non-linked
    if a.startrun and not b.startrun:
      return 1
    if b.startrun and not a.startrun:
      return -1
    # time-linked prizes are listed after non-linked
    if a.starttime and not b.starttime:
      return 1
    if b.starttime and not a.starttime:
      return -1
    # sort by category or name as a fallback
    return cmp(a.category,b.category) or cmp(a.name,b.name)
  prizes = sorted(Prize.objects.filter(event=event),cmp=prizecmp)
  i = 0
  for p in prizes:
    p.sortkey = i
    p.save()
    i += 1

  return HttpResponse(simplejson.dumps({'result': 'Merged %d run(s)' % len(runs) }, use_decimal=True),content_type='application/json;charset=utf-8')

def donate(request, event):
  serverName = request.META['SERVER_NAME'];
  serverURL = "http://" + serverName;
  event = viewutil.get_event(event);

  paypal_dict = {
    "cmd": "_donations",
    "business": event.paypalemail, 
    "item_name": event.receivername,
    "notify_url": serverURL + reverse('tracker.views.ipn'),
    "return_url": serverURL + reverse('tracker.views.paypal_return'),
    "cancel_return": serverURL + reverse('tracker.views.paypal_cancel'),
    "custom": event.id,
    "currency_code": event.paypalcurrency,
  }
  # Create the form instance
  form = PayPalPaymentsForm(button_type="donate", sandbox=event.usepaypalsandbox, initial=paypal_dict)
  context = {"event": event, "form": form.render()}
  return tracker_response(request, "tracker/donate.html", context)

@csrf_exempt
def paypal_cancel(request):
  return tracker_response(request, "tracker/paypal_cancel");

_DONATION_AUTH = "DONATION_AUTH";

@require_POST
@csrf_exempt
def paypal_return(request):
  event = models.Event.objects.get(id=int(request.POST['custom']))
  refererSite = viewutil.get_referer_site(request);
  # This doesn't work on IE, is there a better way to handle this?
  #if refererSite not in ['www.paypal.com', 'www.sandbox.paypal.com']:
  #  f = open('/testdir/exceptd.txt', 'w')
  #  f.write(str(refererSite));
  #  f.close();
  #  return HttpResponse("Permission Denied"); 
  ipnObj = paypalutil.initialize_ipn_object(request); 
  donation, created = paypalutil.auto_create_paypal_donation(ipnObj, event);
  request.session[_DONATION_AUTH] = donation.id;
  return django.shortcuts.redirect('donation_edit');

def donation_edit_auth(request):
  if request.method == 'POST':
    form = DonationCredentialsForm(request.POST);
    if form.is_valid():
      donation = paypalutil.get_paypal_donation(
        paypalemail=form.cleaned_data['paypalemail'],
        amount=form.cleaned_data['amount'],
        transactionid=form.cleaned_data['transactionid'])
      if donation is not None:
        request.session[_DONATION_AUTH] = donation.id;
        return django.shortcuts.redirect('donation_edit');
      else:
        import django.forms.forms as djangoforms;
        errorList = form._errors.setdefault(djangoforms.NON_FIELD_ERRORS, djangoforms.ErrorList());
        errorList.append("Error, no such donation was found");
  else:
    form = DonationCredentialsForm();
  return tracker_response(request, "tracker/donation_edit_auth.html", {'form': form});
      
def donation_edit(request):
  donationId = request.session.get(_DONATION_AUTH, None);
  if donationId is None:
    return django.shortcuts.redirect('donation_edit_auth'); 
  
  donation = Donation.objects.get(pk=donationId);
  
  if request.method == 'POST':
    commentform = DonationCommentForm(data=request.POST);
    bidsform = DonationBidFormSet(donation=donation, data=request.POST);
    if commentform.is_valid() and bidsform.is_valid():
      # maybe do some other post-processing here to check for complete validity  (bid assignment can get pretty hairy)
      if donation.commentstate == 'ABSENT' and 'comment' in commentform.cleaned_data:
        print("Setting comment");
        donation.comment = commentform.cleaned_data['comment'];
        donation.commentstate = "PENDING";
        donation.bidstate = "FLAGGED";
      
      for bidform in bidsform:
        if 'bid' in bidform.cleaned_data:
          bid = bidform.cleaned_data['bid'];
          print(bid);
          if type(bid) == Challenge:
            donation.challengebid_set.add(ChallengeBid(challenge=bid, amount=Decimal(bidform.cleaned_data['amount'])));
          else:
            donation.choicebid_set.add(ChoiceBid(option=bid, amount=Decimal(bidform.cleaned_data['amount'])));
      donation.save();
      # clear out the session information for editing this donation
      request.session[_DONATION_AUTH] = None;
      return tracker_response(request, "tracker/donation_edit_complete.html", {'donation': donation});
  else:
    data = {
      'form-TOTAL_FORMS': u'1',
      'form-INITIAL_FORMS': u'0',
      'form-MAX_NUM_FORMS': u'',
    };
    commentform = DonationCommentForm();
    bidsform = DonationBidFormSet(donation=donation, data=data);
  
  challengeBids = donation.challengebid_set.all();
  choiceBids = donation.choicebid_set.all();
  
  totalAllocated = reduce(lambda x, y: x + y, map(lambda x: x.amount, itertools.chain(challengeBids,choiceBids)), Decimal('0.00'));
  
  challenges = filters.run_model_query('challenge', {'state':'OPENED'}, user=request.user);
  challenges = challenges.select_related('speedrun').annotate(**viewutil.ModelAnnotations['challenge'])
  
  choiceoptions = filters.run_model_query('choiceoption', {'state':'OPENED'}, user=request.user);
  choiceoptions = choiceoptions.select_related('choice', 'choice__speedrun').annotate(**viewutil.ModelAnnotations['choiceoption'])
  
  dumpArray = [{'id': o.id, 'type': 'challenge', 'name': o.name, 'runname': o.speedrun.name, 'count': o.count, 'amount': o.amount, 'goal': o.goal,  'description': o.description} for o in challenges.all()];
  dumpArray.extend([{'id': o.id, 'type': 'choice', 'name': o.name, 'choicename': o.choice.name, 'runname': o.choice.speedrun.name, 'amount': o.amount, 'count': o.count, 'description': o.description, 'choicedescription': o.choice.description} for o in choiceoptions.all()]);
  bidsJson = simplejson.dumps(dumpArray);
  
  return tracker_response(request, "tracker/donation_edit.html", {'donation': donation, 'challengebids': challengeBids, 'choicebids': choiceBids, 'numbids': len(challengeBids) + len(choiceBids), 'totalallocated': totalAllocated, 'totalremaining': donation.amount - totalAllocated, 'bidsform': bidsform, 'commentform': commentform, 'bids': bidsJson});

@require_POST
@csrf_exempt
def ipn(request):
  try:
    event = models.Event.objects.get(id=int(request.POST['custom']))
    ipn_obj = paypalutil.initialize_ipn_object(request);

    ipn_obj.save()

    if not ipn_obj.flag and ipn_obj.payment_status.lower() in ['completed', 'refunded']:
      donation, created = paypalutil.auto_create_paypal_donation(ipn_obj, event);
      if ipn_obj.payment_status.lower() == 'completed':
        donation.transactionstate = 'COMPLETED';
      elif ipn_obj.payment_status.lower() == 'refunded':
        donation.transactionstate = 'CANCELLED';
      donation.save();
    else:
      raise Exception(ipn_obj.flag_info);
  except Exception as inst:
    rr = open('/testdir/except.txt', 'w');
    rr.write(str(inst) + "\n");
    rr.write(ipn_obj.txn_id + "\n");
    rr.write(ipn_obj.payer_email + "\n");
    rr.write(str(ipn_obj.payment_date) + "\n");
    rr.write(str(request.POST['payment_date']) + "\n");
    rr.close(); 

  return HttpResponse("OKAY");
