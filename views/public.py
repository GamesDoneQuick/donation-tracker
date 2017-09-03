from itertools import ifilter

from tracker.models import *
from tracker.forms import *
from . import common as views_common
import tracker.filters as filters
import tracker.viewutil as viewutil

from django.db.models import Count, Sum, Max, Avg, Q, F
import django.core.paginator as paginator
from django.http import HttpResponse,HttpResponseRedirect
from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse
from django.core import serializers

from decimal import Decimal
import json

__all__ = [
  'eventlist',
  'index',
  'bidindex',
  'bid',
  'donorindex',
  'donor',
  'donationindex',
  'donation',
  'runindex',
  'run',
  'prizeindex',
  'prize',
  ]

def eventlist(request):
  return views_common.tracker_response(request, 'tracker/eventlist.html', { 'events' : Event.objects.all() })

def index(request,event=None):
  event = viewutil.get_event(event)
  eventParams = {}

  if event.id:
    eventParams['event'] = event.id

  agg = filters.run_model_query('donation', eventParams).aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
  agg['target'] = event.targetamount
  count = {
    'runs' : filters.run_model_query('run', eventParams).count(),
    'prizes' : filters.run_model_query('prize', eventParams).count(),
    'bids' : filters.run_model_query('bid', eventParams).count(),
    'donors' : filters.run_model_query('donorcache', eventParams).values('donor').distinct().count(),
  }

  if 'json' in request.GET:
    return HttpResponse(json.dumps({'count':count,'agg':agg},ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder),content_type='application/json;charset=utf-8')

  return views_common.tracker_response(request, 'tracker/index.html', { 'agg' : agg, 'count' : count, 'event': event })

def get_bid_children(bid, bids):
  return sorted((bid_info(child, bids) for child in bids if child.parent_id == bid.id), key=lambda child: -child['total'])

def get_bid_ancestors(bid, bids):
  while bid.parent_id:
    if bid.parent_id:
      bid = next(ifilter(lambda parent: parent.id == bid.parent_id, bids))
      yield bid

def bid_info(bid, bids, speedrun=None, event=None):
  return {
    'id': bid.id,
    'name': bid.name,
    'children': get_bid_children(bid, bids),
    'ancestors': list(get_bid_ancestors(bid, bids))[::-1],
    'speedrun': bid.speedrun_name,
    'event': bid.event_name if not bid.speedrun_name else '',
    'description': bid.description,
    'goal': bid.goal,
    'total': bid.total,
    'istarget': bid.istarget,
  }

@cache_page(60)
def bidindex(request, event=None):
  event = viewutil.get_event(event)

  if not event.id:
    return HttpResponseRedirect(reverse('tracker.views.bidindex', args=(Event.objects.latest().short,)))

  bids = Bid.objects.filter(state__in=('OPENED', 'CLOSED')).annotate(speedrun_name=F('speedrun__name'), event_name=F('event__name'))
  if event.id:
    bids = bids.filter(event=event)

  toplevel = [b for b in bids if b.parent_id == None]
  total = sum((b.total for b in toplevel), 0)
  choiceTotal = sum((b.total for b in toplevel if not b.goal), 0)
  challengeTotal = sum((b.total for b in toplevel if b.goal), 0)

  bids = [bid_info(bid, bids) for bid in bids if bid.parent_id == None]

  if event.id:
    bidNameSpan = 2
  else:
    bidNameSpan = 1

  return views_common.tracker_response(request, 'tracker/bidindex.html', { 'bids': bids, 'total': total, 'event': event, 'bidNameSpan' : bidNameSpan, 'choiceTotal': choiceTotal, 'challengeTotal': challengeTotal })

@cache_page(60)
def bid(request, id):
  try:
    orderdict = {
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

    bid = Bid.objects.filter(pk=id,state__in=('OPENED', 'CLOSED')).annotate(speedrun_name=F('speedrun__name'), event_name=F('event__name')).first()
    if not bid:
      raise Bid.DoesNotExist
    event = bid.event
    bid = bid_info(bid, (bid.get_ancestors() | bid.get_descendants()).annotate(speedrun_name=F('speedrun__name'), event_name=F('event__name')))

    if not bid['istarget']:
      return views_common.tracker_response(request, 'tracker/bid.html', { 'event': event, 'bid' : bid})
    else:
      donationBids = DonationBid.objects.filter(bid_id=bid['id']).filter(viewutil.DonationBidAggregateFilter)
      donationBids = donationBids.select_related('donation','donation__donor').order_by('-donation__timereceived')
      donationBids = views_common.fixorder(donationBids, orderdict, sort, order)
      comments = 'comments' in request.GET
      return views_common.tracker_response(request, 'tracker/bid.html', { 'event': event, 'bid' : bid, 'comments' : comments, 'donationBids' : donationBids })

  except Bid.DoesNotExist:
    return views_common.tracker_response(request, template='tracker/badobject.html', status=404)


@cache_page(60)
def donorindex(request,event=None):
  event = viewutil.get_event(event)
  orderdict = {
    'total' : ('donation_total',    ),
    'max'   : ('donation_max',      ),
    'avg'   : ('donation_avg',      ),
    'count' : ('donation_count',    ),
  }
  page = request.GET.get('page', 1)
  sort = request.GET.get('sort', 'total')

  if sort not in orderdict:
    sort = 'total'

  try:
    order = int(request.GET.get('order', -1))
  except ValueError:
    order = -1

  donors = DonorCache.objects.filter(event=event.id if event.id else None).exclude(donor__visibility='ANON').order_by(*orderdict[sort])
  if order == -1:
    donors = donors.reverse()

  pages = paginator.Paginator(donors,50)

  try:
    pageinfo = pages.page(page)
  except paginator.PageNotAnInteger:
    pageinfo = pages.page(1)
  except paginator.EmptyPage:
    pageinfo = pages.page(pages.num_pages)
    page = pages.num_pages
  donors = pageinfo.object_list

  return views_common.tracker_response(request, 'tracker/donorindex.html', { 'donors' : donors, 'event' : event, 'pageinfo' : pageinfo, 'page' : page, 'sort' : sort, 'order' : order })


@cache_page(60)
def donor(request, id, event=None):
  try:
    event = viewutil.get_event(event)
    cache = DonorCache.objects.get(donor=id,event=event.id if event.id else None)
    if cache.visibility == 'ANON':
      return views_common.tracker_response(request, template='tracker/badobject.html', status=404)
    donations = cache.donation_set.filter(transactionstate='COMPLETED')

    if event.id:
      donations = donations.filter(event=event)

    comments = 'comments' in request.GET

    return views_common.tracker_response(request, 'tracker/donor.html', { 'cache' : cache, 'donations' : donations, 'comments' : comments, 'event' : event })
  except DonorCache.DoesNotExist:
    return views_common.tracker_response(request, template='tracker/badobject.html', status=404)


@cache_page(60)
def donationindex(request,event=None):
  event = viewutil.get_event(event)
  orderdict = {
    'amount' : ('amount', ),
    'time'   : ('timereceived', ),
  }
  page = request.GET.get('page', 1)
  sort = request.GET.get('sort', 'time')

  try:
    order = int(request.GET.get('order', -1))
  except ValueError:
    order = -1

  donations = Donation.objects.filter(transactionstate='COMPLETED')

  if event.id:
    donations = donations.filter(event=event)
  donations = views_common.fixorder(donations, orderdict, sort, order)

  agg = donations.aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
  donations = donations.select_related('donor')
  pages = paginator.Paginator(donations,50)
  try:
    pageinfo = pages.page(page)
  except paginator.PageNotAnInteger:
    pageinfo = pages.page(1)
  except paginator.EmptyPage:
    pageinfo = pages.page(pages.num_pages)
    page = pages.num_pages
  donations = pageinfo.object_list

  return views_common.tracker_response(request, 'tracker/donationindex.html', { 'donations' : donations, 'pageinfo' :  pageinfo, 'page' : page, 'agg' : agg, 'sort' : sort, 'order' : order, 'event': event })

@cache_page(300)
def donation(request,id):
  try:
    donation = Donation.objects.get(pk=id)

    if donation.transactionstate != 'COMPLETED':
      return views_common.tracker_response(request, 'tracker/badobject.html')

    event = donation.event
    donor = donation.donor
    donationbids = DonationBid.objects.filter(donation=id).select_related('bid','bid__speedrun','bid__event')

    return views_common.tracker_response(request, 'tracker/donation.html', { 'event': event, 'donation' : donation, 'donor' : donor, 'donationbids' : donationbids })

  except Donation.DoesNotExist:
    return views_common.tracker_response(request, template='tracker/badobject.html', status=404)

@cache_page(300)
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

  runs = filters.run_model_query('run', searchParams)
  runs = runs.annotate(hasbids=Sum('bids'))

  return views_common.tracker_response(request, 'tracker/runindex.html', { 'searchForm': searchForm, 'runs' : runs, 'event': event })

@cache_page(300)
def run(request,id):
  try:
    run = SpeedRun.objects.get(pk=id)
    runners = run.runners.all()
    event = run.event
    bids = filters.run_model_query('bid', {'run': id})
    bids = viewutil.get_tree_queryset_descendants(Bid, bids, include_self=True).select_related('speedrun','event', 'parent').prefetch_related('options')
    topLevelBids = filter(lambda bid: bid.parent == None, bids)

    return views_common.tracker_response(request, 'tracker/run.html', { 'event': event, 'run' : run, 'runners': runners, 'bids' : topLevelBids })

  except SpeedRun.DoesNotExist:
    return views_common.tracker_response(request, template='tracker/badobject.html', status=404)

@cache_page(1800)
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

  prizes = filters.run_model_query('prize', searchParams)
  prizes = prizes.select_related('startrun','endrun','category').prefetch_related('prizewinner_set')
  return views_common.tracker_response(request, 'tracker/prizeindex.html', { 'searchForm': searchForm, 'prizes' : prizes, 'event': event })

@cache_page(1800)
def prize(request,id):
  try:
    prize = Prize.objects.get(pk=id)
    event = prize.event
    games = None
    category = None

    if prize.startrun:
      games = SpeedRun.objects.filter(starttime__gte=SpeedRun.objects.get(pk=prize.startrun.id).starttime,endtime__lte=SpeedRun.objects.get(pk=prize.endrun.id).endtime)

    if prize.category:
      category = PrizeCategory.objects.get(pk=prize.category.id)

    return views_common.tracker_response(request, 'tracker/prize.html', { 'event': event, 'prize' : prize, 'games' : games,  'category': category })
  except Prize.DoesNotExist:
    return views_common.tracker_response(request, template='tracker/badobject.html', status=404)

