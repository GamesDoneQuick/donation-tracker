import django

from django import shortcuts
from django.shortcuts import render,render_to_response, redirect

from django.db import connection
from django.db.models import Count,Sum,Max,Avg,Q
from django.db.utils import ConnectionDoesNotExist,IntegrityError
from django.db import transaction

from django.forms import ValidationError

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
import json

from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.forms import PayPalIPNForm

from tracker.models import *
from tracker.forms import *
import tracker.filters as filters

import tracker.viewutil as viewutil
import tracker.paypalutil as paypalutil

from django.core.serializers.json import DjangoJSONEncoder

import gdata.spreadsheet.service
import gdata.spreadsheet.text_db

from decimal import Decimal
import sys
import datetime
import settings
import logutil as log
import pytz
import random
import decimal
import re
import dateutil.parser
import itertools
import urllib2

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
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
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
    eventParams['event'] = event.id
  agg = filters.run_model_query('donation', eventParams, user=request.user, mode='user').aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
  agg['target'] = event.targetamount
  count = {
    'runs' : filters.run_model_query('run', eventParams, user=request.user).count(),
    'prizes' : filters.run_model_query('prize', eventParams, user=request.user).count(),
    'bids' : filters.run_model_query('bid', eventParams, user=request.user).count(),
    'donors' : filters.run_model_query('donor', eventParams, user=request.user).distinct().count(),
  }

  if 'json' in request.GET:
    return HttpResponse(json.dumps({'count':count,'agg':agg},ensure_ascii=False),content_type='application/json;charset=utf-8')
  elif 'jsonp' in request.GET:
    callback = request.GET['jsonp']
    return HttpResponse('%s(%s);' % (callback, json.dumps({'count':count,'agg':agg},ensure_ascii=False)), content_type='text/javascript;charset=utf-8')
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
  'bid'           : Bid,
  'donationbid'   : DonationBid,
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
fkmap = { 'winners': 'donor', 'speedrun': 'run', 'startrun': 'run', 'endrun': 'run', 'category': 'prizecategory', 'parent': 'bid'}

related = {
  'bid'          : [ 'speedrun', 'event', 'parent' ],
  'donation'     : [ 'donor' ],
  'prize'        : [ 'category', 'startrun', 'endrun' ],
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
  if visibility == 'ANON':
    fields[prefix + 'alias'] = None

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

@never_cache
def search(request):
  authorizedUser = request.user.has_perm('tracker.can_search')
  #  return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
  try:
    searchtype = request.GET['type']
    qs = filters.run_model_query(searchtype, request.GET, user=request.user, mode='admin' if authorizedUser else 'user')
    if searchtype in related:
      qs = qs.select_related(*related[searchtype])
    if searchtype in defer:
      qs = qs.defer(*defer[searchtype])
    qs = qs.annotate(**viewutil.ModelAnnotations.get(searchtype,{}))
    if searchtype == 'bid' or searchtype == 'allbids':
      qs = viewutil.CalculateBidQueryAnnotations(qs)
    json = json.loads(serializers.serialize('json', qs, ensure_ascii=False))
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
      if not authorizedUser:
        donor_privacy_filter(searchtype, o['fields'])
        donation_privacy_filter(searchtype, o['fields'])
    resp = HttpResponse(json.dumps(json,ensure_ascii=False),content_type='application/json;charset=utf-8')
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
        continue
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
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
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
    return HttpResponse(json.dumps({'error': 'Key Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except FieldError, e:
    return HttpResponse(json.dumps({'error': 'Field Error, malformed add parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValueError, e:
    return HttpResponse(json.dumps({'error': u'Value Error', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

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
    return HttpResponse(json.dumps({'result': u'Object %s of type %s deleted' % (request.POST['id'],request.POST['type'])}, ensure_ascii=False), content_type='application/json;charset=utf-8')
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
    print(request.GET)
    edittype = request.GET['type']
    if not request.user.has_perm('tracker.change_' + permmap.get(edittype,edittype)):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    Model = modelmap[edittype]
    obj = Model.objects.get(pk=request.GET['id'])
    changed = []
    for k,v in request.GET.items():
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
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
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
    return HttpResponse(json.dumps({'error': 'Key Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except FieldError, e:
    return HttpResponse(json.dumps({'error': 'Field Error, malformed edit parameters', 'exception': unicode(e)}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
  except ValueError, e:
    return HttpResponse(json.dumps({'error': u'Value Error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

def bidindex(request, event=None):
  event = viewutil.get_event(event)
  searchForm = BidSearchForm(request.GET)
  if not searchForm.is_valid():
    return HttpResponse('Invalid filter form', status=400)
  searchParams = {}
  searchParams.update(request.GET)
  searchParams.update(searchForm.cleaned_data)
  if event.id:
    searchParams['event'] = event.id
  bids = filters.run_model_query('bid', searchParams, user=request.user)
  bids = bids.filter(parent=None)
  total = bids.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
  choiceTotal = bids.filter(goal=None).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
  challengeTotal = bids.exclude(goal=None).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
  bids = viewutil.get_tree_queryset_descendants(Bid, bids, include_self=True).prefetch_related('options')
  bids = bids.filter(parent=None)
  if event.id:
    bidNameSpan = 2
  else:
    bidNameSpan = 1
  return tracker_response(request, 'tracker/bidindex.html', { 'searchForm': searchForm, 'bids': bids, 'total': total, 'event': event, 'bidNameSpan' : bidNameSpan, 'choiceTotal': choiceTotal, 'challengeTotal': challengeTotal })

def bid(request, id):
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
    bid = Bid.objects.get(pk=id)
    bids = bid.get_descendants(include_self=True).select_related('speedrun','event', 'parent').prefetch_related('options')
    ancestors = bid.get_ancestors()
    event = bid.event if bid.event else bid.speedrun.event
    if not bid.istarget:
      return tracker_response(request, 'tracker/bid.html', { 'event': event, 'bid' : bid, 'ancestors' : ancestors })
    else:
      donationBids = DonationBid.objects.filter(bid__exact=id).filter(viewutil.DonationBidAggregateFilter)
      donationBids = donationBids.select_related('donation','donation__donor').order_by('-donation__timereceived')
      donationBids = fixorder(donationBids, orderdict, sort, order)
      comments = 'comments' in request.GET
      return tracker_response(request, 'tracker/bid.html', { 'event': event, 'bid' : bid, 'comments' : comments, 'donationBids' : donationBids, 'ancestors' : ancestors })
  except Bid.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

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

  searchForm = DonorSearchForm(request.GET)
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400)
  searchParams = {}
  #searchParams.update(request.GET)
  #searchParams.update(searchForm.cleaned_data)
  if event.id:
    searchParams['event'] = event.id

  #donors = Donor.objects.filter(donation__event=event, donation__testdonation=False)#.filter(donation__testdonation=False)

  donors = filters.run_model_query('donor', searchParams, user=request.user)
  donors = donors.annotate(**viewutil.ModelAnnotations['donor'])

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
    donations = donor.donation_set.filter(transactionstate='COMPLETED')
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
    order = -1
  searchForm = DonationSearchForm(request.GET)
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400)
  searchParams = {}
  searchParams.update(request.GET)
  searchParams.update(searchForm.cleaned_data)
  if event.id:
    searchParams['event'] = event.id
  donations = filters.run_model_query('donation', searchParams, user=request.user)
  donations = fixorder(donations, orderdict, sort, order)
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
    event = donation.event
    donor = donation.donor
    donationbids = DonationBid.objects.filter(donation=id).select_related('bid','bid__speedrun','bid__event')
    return tracker_response(request, 'tracker/donation.html', { 'event': event, 'donation' : donation, 'donor' : donor, 'donationbids' : donationbids })
  except Donation.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def runindex(request,event=None):
  event = viewutil.get_event(event)
  searchForm = RunSearchForm(request.GET)
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400)
  searchParams = {}
  searchParams.update(request.GET)
  searchParams.update(searchForm.cleaned_data)
  if event.id:
    searchParams['event'] = event.id
  runs = filters.run_model_query('run', searchParams, user=request.user)
  runs = runs.select_related('runners').annotate(hasbids=Sum('bids'))
  return tracker_response(request, 'tracker/runindex.html', { 'searchForm': searchForm, 'runs' : runs, 'event': event })

def run(request,id):
  try:
    run = SpeedRun.objects.get(pk=id)
    runners = run.runners.all()
    event = run.event
    bids = filters.run_model_query('bid', {'run': id}, user=request.user)
    bids = viewutil.get_tree_queryset_descendants(Bid, bids, include_self=True).select_related('speedrun','event', 'parent').prefetch_related('options')
    bidsCache = viewutil.FixupBidAnnotations(bids)
    topLevelBids = filter(lambda bid: bid.parent == None, bids)
    bids = topLevelBids

    return tracker_response(request, 'tracker/run.html', { 'event': event, 'run' : run, 'runners': runners, 'bids' : topLevelBids, 'bidsCache' : bidsCache })
  except SpeedRun.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

def prizeindex(request,event=None):
  event = viewutil.get_event(event)
  searchForm = PrizeSearchForm(request.GET)
  if not searchForm.is_valid():
    return HttpResponse('Invalid Search Data', status=400)
  searchParams = {}
  searchParams.update(request.GET)
  searchParams.update(searchForm.cleaned_data)
  if event.id:
    searchParams['event'] = event.id
  prizes = filters.run_model_query('prize', searchParams, user=request.user)
  prizes = prizes.select_related('startrun','endrun','category').prefetch_related('winners')
  return tracker_response(request, 'tracker/prizeindex.html', { 'searchForm': searchForm, 'prizes' : prizes })

def prize(request,id):
  try:
    prize = Prize.objects.get(pk=id)
    event = prize.event
    games = None
    category = None
    contributors = prize.contributors.all()
    if prize.startrun:
      games = SpeedRun.objects.filter(starttime__gte=SpeedRun.objects.get(pk=prize.startrun.id).starttime,endtime__lte=SpeedRun.objects.get(pk=prize.endrun.id).endtime)
    if prize.category:
      category = PrizeCategory.objects.get(pk=prize.category.id)
    return tracker_response(request, 'tracker/prize.html', { 'event': event, 'prize' : prize, 'games' : games,  'category': category, 'contributors': contributors })
  except Prize.DoesNotExist:
    return tracker_response(request, template='tracker/badobject.html', status=404)

@never_cache
def prize_donors(request,id):
  try:
    if not request.user.has_perm('tracker.change_prize'):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    resp = HttpResponse(json.dumps(Prize.objects.get(pk=id).eligible_donors()),content_type='application/json;charset=utf-8')
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
  except Prize.DoesNotExist:
    return HttpResponse(json.dumps({'error': 'Prize id does not exist'}),status=404,content_type='application/json;charset=utf-8')

@csrf_exempt
@never_cache
#TODO: combine this with the viewutil code, make sure it works correctly, and then actually use this
# for a simplified prize drawing page
def draw_prize(request,id):
  try:
    if not request.user.has_perm('tracker.change_prize'):
      return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
    prize = Prize.objects.get(pk=id)
    eligible = prize.eligible_donors()
    key = hash(json.dumps(eligible))
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    if prize.maxed_winners():
      return HttpResponse(json.dumps({'error': 'Prize already has a winner', 'winners': [winner.id for winner in prize.winners.all()]},ensure_ascii=False),status=400,content_type='application/json;charset=utf-8')
    if not eligible:
      return HttpResponse(json.dumps({'error': 'Prize has no eligible donors'}),status=409,content_type='application/json;charset=utf-8')
    if request.method == 'GET':
      return HttpResponse(json.dumps({'key': key}),content_type='application/json;charset=utf-8')
    elif request.method == 'POST':
      try:
        okey = type(key)(request.POST['key'])
      except (ValueError,KeyError),e:
        return HttpResponse(json.dumps({'error': 'Key field was missing or malformed', 'exception': '%s %s' % (type(e),e)},ensure_ascii=False),status=400,content_type='application/json;charset=utf-8')
      if key != okey:
        return HttpResponse(json.dumps({'error': 'Key field did not match expected value', 'expected': key}),status=400,content_type='application/json;charset=utf-8')
      try:
        random.seed(request.POST.get('seed',None))
      except TypeError: # not sure how this could happen but hey
        return HttpResponse(json.dumps({'error': 'Seed parameter was unhashable'}),status=400,content_type='application/json;charset=utf-8')
      psum = reduce(lambda a,b: a+b['weight'], eligible, 0.0)
      result = random.random() * psum
      ret = {'sum': psum, 'result': result}
      winRecord = None
      for d in eligible:
        if result < d['weight']:
          winRecord = PrizeWinner.objects.create(prize=prize, winner=Donor.objects.get(pk=d['donor']))
          winRecord.save()
          break
        result -= d['weight']
      if winRecord:
        ret['winner'] = winRecord.winner.id
      log.change(request,prize,u'Picked winner. %.2f,%.2f' % (psum,result))
      return HttpResponse(json.dumps(ret, ensure_ascii=False),content_type='application/json;charset=utf-8')
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
    numRuns = viewutil.MergeScheduleGDoc(event)
  except Exception as e:
    return HttpResponse(json.dumps({'error': e.message }),status=500,content_type='application/json;charset=utf-8')

  return HttpResponse(json.dumps({'result': 'Merged %d run(s)' % numRuns }),content_type='application/json;charset=utf-8')

@csrf_exempt
def paypal_cancel(request):
  return tracker_response(request, "tracker/paypal_cancel.html")

@require_POST
@csrf_exempt
def paypal_return(request):
  ipnObj = paypalutil.initialize_ipn_object(request)
  return tracker_response(request, "tracker/paypal_return.html", { 'firstname': ipnObj.first_name, 'lastname': ipnObj.last_name, 'amount': ipnObj.mc_gross })

@transaction.commit_on_success
@csrf_exempt
def donate(request, event):
  event = viewutil.get_event(event)
  bidsFormPrefix = "bidsform"
  prizeFormPrefix = "prizeForm"
  if request.method == 'POST':
    commentform = DonationEntryForm(data=request.POST)
    if commentform.is_valid():
      prizesform = PrizeTicketFormSet(amount=commentform.cleaned_data['amount'], data=request.POST, prefix=prizeFormPrefix)
      bidsform = DonationBidFormSet(amount=commentform.cleaned_data['amount'], data=request.POST, prefix=bidsFormPrefix)
      if bidsform.is_valid() and prizesform.is_valid():
        try:
          donation = models.Donation.objects.create(amount=commentform.cleaned_data['amount'], timereceived=pytz.utc.localize(datetime.datetime.utcnow()), domain='PAYPAL', domainId=str(random.getrandbits(128)), event=event, testdonation=event.usepaypalsandbox)
          if commentform.cleaned_data['comment']:
            donation.comment = commentform.cleaned_data['comment']
            donation.commentstate = "PENDING"
            if commentform.cleaned_data['hasbid']:
              donation.bidstate = "FLAGGED"
          donation.requestedvisibility = commentform.cleaned_data['requestedvisibility']
          donation.requestedalias = commentform.cleaned_data['requestedalias']
          donation.requestedemail = commentform.cleaned_data['requestedemail']
          donation.currency = event.paypalcurrency
          for bidform in bidsform:
            if 'bid' in bidform.cleaned_data and bidform.cleaned_data['bid']:
              bid = bidform.cleaned_data['bid']
              donation.bids.add(DonationBid(bid=bid, amount=Decimal(bidform.cleaned_data['amount'])))
          for prizeform in prizesform:
            if 'prize' in prizeform.cleaned_data and prizeform.cleaned_data['prize']:
              prize = prizeform.cleaned_data['prize']
              donation.tickets.add(PrizeTicket(prize=prize, amount=Decimal(prizeform.cleaned_data['amount'])))
          donation.full_clean()
          donation.save()
        except Exception as e:
          transaction.rollback()
          raise e

        serverName = request.META['SERVER_NAME']
        serverURL = "http://" + serverName

        paypal_dict = {
          "amount": str(donation.amount),
          "cmd": "_donations",
          "business": donation.event.paypalemail,
          "item_name": donation.event.receivername,
          "notify_url": serverURL + reverse('tracker.views.ipn'),
          "return_url": serverURL + reverse('tracker.views.paypal_return'),
          "cancel_return": serverURL + reverse('tracker.views.paypal_cancel'),
          "custom": str(donation.id) + ":" + donation.domainId,
          "currency_code": donation.event.paypalcurrency,
        }
        # Create the form instance
        form = PayPalPaymentsForm(button_type="donate", sandbox=donation.event.usepaypalsandbox, initial=paypal_dict)
        context = {"event": donation.event, "form": form }
        return tracker_response(request, "tracker/paypal_redirect.html", context)
    else:
      bidsform = DonationBidFormSet(amount=Decimal('0.00'), data=request.POST, prefix=bidsFormPrefix)
      prizesform = PrizeTicketFormSet(amount=Decimal('0.00'), data=request.POST, prefix=prizeFormPrefix)
  else:
    commentform = DonationEntryForm()
    bidsform = DonationBidFormSet(amount=Decimal('0.00'), prefix=bidsFormPrefix)
    prizesform = PrizeTicketFormSet(amount=Decimal('0.00'), prefix=prizeFormPrefix)

  def bid_label(bid):
    if not bid.amount:
      bid.amount = Decimal("0.00")
    result = bid.fullname()
    if bid.speedrun:
      result = bid.speedrun.name + " : " + result
    result += " $" + ("%0.2f" % bid.amount)
    if bid.goal:
      result += " / " + ("%0.2f" % bid.goal)
    return result

  def bid_parent_info(bid):
    if bid != None:
      return {'name': bid.name, 'description': bid.description, 'parent': bid_parent_info(bid.parent) }
    else:
      return None

  def bid_info(bid):
    result = {'id': bid.id, 'name': bid.name, 'description': bid.description, 'label': bid_label(bid), 'count': bid.count, 'amount': Decimal(bid.amount or '0.00'), 'goal': Decimal(bid.goal or '0.00'), 'parent': bid_parent_info(bid.parent)}
    if bid.speedrun:
      result['runname'] = bid.speedrun.name
    if bid.suggestions.exists():
      result['suggested'] = list(map(lambda x: x.name, bid.suggestions.all()))
    return result

  bids = filters.run_model_query('bidtarget', {'state':'OPENED', 'event':event.id }, user=request.user).select_related('parent').prefetch_related('suggestions')

  allPrizes = filters.run_model_query('prize', {'feed': 'current', 'event': event.id })

  prizes = allPrizes.filter(ticketdraw=False)

  dumpArray = [bid_info(o) for o in bids.all()]
  bidsJson = json.dumps(dumpArray)

  ticketPrizes = allPrizes.filter(ticketdraw=True)

  def prize_info(prize):
    result = {'id': prize.id, 'name': prize.name, 'description': prize.description, 'minimumbid': prize.minimumbid, 'maximumbid': prize.maximumbid}
    return result

  dumpArray = [prize_info(o) for o in ticketPrizes.all()]
  ticketPrizesJson = json.dumps(dumpArray)

  return tracker_response(request, "tracker/donate.html", { 'event': event, 'bidsform': bidsform, 'prizesform': prizesform, 'commentform': commentform, 'hasBids': bids.count() > 0, 'bidsJson': bidsJson, 'hasTicketPrizes': ticketPrizes.count() > 0, 'ticketPrizesJson': ticketPrizesJson, 'prizes': prizes})

@require_POST
@csrf_exempt
def ipn(request):
  try:
    ipnObj = paypalutil.initialize_ipn_object(request)

    ipnObj.save()

    custom = request.POST['custom']
    toks = custom.split(':')
    pk = int(toks[0])
    domainId = long(toks[1])
    donationF = Donation.objects.filter(pk=pk, domain='PAYPAL', domainId=domainId)
    if donationF:
      donation = donationF[0]
    else:
      donation = None

    donation = paypalutil.initialize_paypal_donation(donation, ipnObj)

    donation.save()

    # This is mostly for information gathering
    if ipnObj.flag or ipnObj.payment_status.lower() not in ['completed', 'refunded']:
      raise Exception(ipnObj.flag_info)

    if donation.transactionstate == 'COMPLETED':
      # TODO: this should eventually share code with the 'search' method, to
      postbackData = {
        'id': donation.id,
        'timereceived': str(donation.timereceived),
        'comment': donation.comment,
        'amount': donation.amount,
        'donor__firstname': donation.donor.firstname,
        'donor__lastname': donation.donor.lastname,
        'donor__alias': donation.donor.alias,
        'donor__visibility': donation.donor.visibility,
        'donor__visiblename': donation.donor.visible_name(),
      }
      postbackJSon = json.dumps(postbackData)
      postbacks = PostbackURL.objects.filter(event=donation.event)
      for postback in postbacks:
        opener = urllib2.build_opener()
        req = urllib2.Request(postback.url, postbackJSon, headers={'Content-Type': 'application/json; charset=utf-8'})
        response = opener.open(req, timeout=5)

  except Exception as inst:
    rr = open('/var/www/log/except.txt', 'w+')
    rr.write(str(inst) + "\n")
    rr.write(ipnObj.txn_id + "\n")
    rr.write(ipnObj.payer_email + "\n")
    rr.write(str(ipnObj.payment_date) + "\n")
    rr.write(str(request.POST['payment_date']) + "\n")
    rr.close()

  return HttpResponse("OKAY")
