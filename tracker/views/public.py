import json

import django.core.paginator as paginator
from django.conf import settings
from django.db.models import Count, Sum, Max, Avg, F, FloatField
from django.db.models.functions import Coalesce, Cast
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.views.decorators.cache import cache_page

import tracker.search_filters as filters
import tracker.viewutil as viewutil
from tracker.models import (
    Bid,
    Donation,
    DonationBid,
    DonorCache,
    Event,
    Prize,
    SpeedRun,
)
from . import common as views_common

__all__ = [
    'eventlist',
    'index',
    'bidindex',
    'bid_detail',
    'donorindex',
    'donor_detail',
    'donationindex',
    'donation_detail',
    'runindex',
    'run_detail',
    'prizeindex',
    'prize_detail',
]

from tracker.decorators import no_querystring


def page_or_404(objects, page):
    try:
        return paginator.Paginator(objects, 50).page(page)
    except paginator.PageNotAnInteger:
        raise Http404
    except paginator.EmptyPage:
        raise Http404


@no_querystring
def eventlist(request):
    return views_common.tracker_response(
        request, 'tracker/eventlist.html', {'events': Event.objects.all()}
    )


def index(request, event=None):
    event = viewutil.get_event(event)
    eventParams = {}

    if event.id:
        eventParams['event'] = event.id

    agg = Donation.objects.filter(
        transactionstate='COMPLETED', testdonation=False, **eventParams
    ).aggregate(
        amount=Cast(Coalesce(Sum('amount'), 0), output_field=FloatField()),
        count=Count('amount'),
        max=Cast(Coalesce(Max('amount'), 0), output_field=FloatField()),
        avg=Cast(Coalesce(Avg('amount'), 0), output_field=FloatField()),
    )
    agg['target'] = float(event.targetamount)
    count = {
        'runs': filters.run_model_query('run', eventParams).count(),
        'prizes': filters.run_model_query('prize', eventParams).count(),
        'bids': filters.run_model_query('bid', eventParams).count(),
        'donors': filters.run_model_query('donorcache', eventParams)
        .values('donor')
        .distinct()
        .count(),
    }

    if 'json' in request.GET:
        return HttpResponse(
            json.dumps({'count': count, 'agg': agg}, ensure_ascii=False,),
            content_type='application/json;charset=utf-8',
        )

    return views_common.tracker_response(
        request, 'tracker/index.html', {'agg': agg, 'count': count, 'event': event}
    )


def get_bid_children(bid, bids):
    return sorted(
        (get_bid_info(child, bids) for child in bids if child.parent_id == bid.id),
        key=lambda child: -child['total'],
    )


def get_bid_ancestors(bid, bids):
    parent = bid
    while parent:
        parent = next((b for b in bids if parent.parent_id == b.id), None)
        if parent:
            yield parent


def get_bid_info(bid, bids=None):
    bids = bids or []
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
@no_querystring
def bidindex(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return HttpResponseRedirect(
            reverse('tracker:bidindex', args=(Event.objects.latest().short,))
        )

    bids = Bid.objects.filter(state__in=('OPENED', 'CLOSED'), event=event).annotate(
        speedrun_name=F('speedrun__name'), event_name=F('event__name')
    )

    toplevel = [b for b in bids if b.parent_id is None]
    total = sum((b.total for b in toplevel), 0)
    choiceTotal = sum((b.total for b in toplevel if not b.goal), 0)
    challengeTotal = sum((b.total for b in toplevel if b.goal), 0)

    bids = [get_bid_info(bid, bids) for bid in bids if bid.parent_id is None]

    return views_common.tracker_response(
        request,
        'tracker/bidindex.html',
        {
            'bids': bids,
            'total': total,
            'event': event,
            'choiceTotal': choiceTotal,
            'challengeTotal': challengeTotal,
        },
    )


@cache_page(60)
def bid_detail(request, pk):
    try:
        bid = (
            Bid.objects.filter(pk=pk, state__in=('OPENED', 'CLOSED'))
            .select_related('event')
            .annotate(speedrun_name=F('speedrun__name'), event_name=F('event__name'))
            .first()
        )
        if not bid:
            raise Bid.DoesNotExist
        bid_info = get_bid_info(
            bid,
            (bid.get_ancestors() | bid.get_descendants())
            .filter(state__in=('OPENED', 'CLOSED'))
            .annotate(speedrun_name=F('speedrun__name'), event_name=F('event__name')),
        )

        page = request.GET.get('page', 1)
        page_info = page_or_404(
            bid.bids.filter(donation__transactionstate='COMPLETED')
            .select_related('donation')
            .prefetch_related('donation__donor__cache'),
            request.GET.get('page', 1),
        )

        return views_common.tracker_response(
            request,
            'tracker/bid.html',
            {
                'bid': bid_info,
                'donations': page_info.object_list,
                'event': bid.event,
                'pageinfo': page_info,
                'page': page,
            },
        )

    except Bid.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


@cache_page(60)
def donorindex(request, event=None):
    event = viewutil.get_event(event)
    orderdict = {
        'total': ('donation_total',),
        'max': ('donation_max',),
        'avg': ('donation_avg',),
        'count': ('donation_count',),
    }
    page = request.GET.get('page', 1)
    sort = request.GET.get('sort', 'total')

    if sort not in orderdict:
        sort = 'total'

    try:
        order = int(request.GET.get('order', -1))
    except ValueError:
        order = -1

    donors = (
        DonorCache.objects.filter(event=event.id if event.id else None)
        .exclude(donor__visibility='ANON')
        .order_by(*orderdict[sort])
    )
    if order == -1:
        donors = donors.reverse()

    pages = paginator.Paginator(donors, 50)

    try:
        pageinfo = pages.page(page)
    except paginator.PageNotAnInteger:
        pageinfo = pages.page(1)
    except paginator.EmptyPage:
        pageinfo = pages.page(pages.num_pages)
        page = pages.num_pages
    donors = pageinfo.object_list

    return views_common.tracker_response(
        request,
        'tracker/donorindex.html',
        {
            'donors': donors,
            'event': event,
            'pageinfo': pageinfo,
            'page': page,
            'sort': sort,
            'order': order,
        },
    )


@cache_page(60)
@no_querystring
def donor_detail(request, pk, event=None):
    try:
        event = viewutil.get_event(event)
        cache = DonorCache.objects.get(donor=pk, event=event.id if event.id else None)
        if cache.visibility == 'ANON':
            return views_common.tracker_response(
                request, template='tracker/badobject.html', status=404
            )
        donations = cache.donation_set.filter(transactionstate='COMPLETED')

        # TODO: double check that this is(n't) needed
        if event.id:
            donations = donations.filter(event=event)

        comments = False
        # comments = 'comments' in request.GET # TODO: restore this

        return views_common.tracker_response(
            request,
            'tracker/donor.html',
            {
                'cache': cache,
                'donations': donations,
                'comments': comments,
                'event': event,
            },
        )
    except DonorCache.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


@cache_page(60)
def donationindex(request, event=None):
    event = viewutil.get_event(event)
    orderdict = {
        'amount': ('amount',),
        'time': ('timereceived',),
    }
    page = request.GET.get('page', 1)
    sort = request.GET.get('sort', 'time')

    if sort not in orderdict:
        sort = 'time'

    try:
        order = int(request.GET.get('order', -1))
    except ValueError:
        order = -1

    donations = Donation.objects.filter(transactionstate='COMPLETED')

    if event.id:
        donations = donations.filter(event=event)
    donations = views_common.fixorder(donations, orderdict, sort, order)

    agg = donations.aggregate(
        amount=Sum('amount'),
        count=Count('amount'),
        max=Max('amount'),
        avg=Avg('amount'),
    )
    donations = donations.select_related('donor')
    pages = paginator.Paginator(donations, 50)
    try:
        pageinfo = pages.page(page)
    except paginator.PageNotAnInteger:
        pageinfo = pages.page(1)
    except paginator.EmptyPage:
        pageinfo = pages.page(pages.num_pages)
        page = pages.num_pages
    donations = pageinfo.object_list

    return views_common.tracker_response(
        request,
        'tracker/donationindex.html',
        {
            'donations': donations,
            'pageinfo': pageinfo,
            'page': page,
            'agg': agg,
            'sort': sort,
            'order': order,
            'event': event,
        },
    )


@cache_page(300)
def donation_detail(request, pk):
    try:
        donation = Donation.objects.get(pk=pk)

        if donation.transactionstate != 'COMPLETED':
            return views_common.tracker_response(request, 'tracker/badobject.html')

        event = donation.event
        donor = donation.donor
        donationbids = DonationBid.objects.filter(
            donation=pk, bid__state__in=['OPENED', 'CLOSED']
        ).select_related('bid', 'bid__speedrun', 'bid__event')

        return views_common.tracker_response(
            request,
            'tracker/donation.html',
            {
                'event': event,
                'donation': donation,
                'donor': donor,
                'donationbids': donationbids,
            },
        )

    except Donation.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


@cache_page(300)
def runindex(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return HttpResponseRedirect(
            reverse('tracker:runindex', args=(Event.objects.latest().short,))
        )

    searchParams = {}
    searchParams['event'] = event.id

    runs = filters.run_model_query('run', searchParams)
    runs = runs.annotate(hasbids=Sum('bids'))

    return views_common.tracker_response(
        request, 'tracker/runindex.html', {'runs': runs, 'event': event},
    )


@cache_page(300)
def run_detail(request, pk):
    try:
        run = SpeedRun.objects.get(pk=pk)
        runners = run.runners.all()
        event = run.event
        bids = filters.run_model_query('bid', {'run': pk})
        bids = (
            viewutil.get_tree_queryset_descendants(Bid, bids, include_self=True)
            .select_related('speedrun', 'event', 'parent')
            .prefetch_related('options')
        )
        topLevelBids = [bid for bid in bids if bid.parent is None]

        return views_common.tracker_response(
            request,
            'tracker/run.html',
            {'event': event, 'run': run, 'runners': runners, 'bids': topLevelBids},
        )

    except SpeedRun.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


@cache_page(1800)
def prizeindex(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return HttpResponseRedirect(
            reverse('tracker:prizeindex', args=(Event.objects.latest().short,))
        )

    searchParams = {}
    searchParams['event'] = event.id

    prizes = filters.run_model_query('prize', searchParams)
    prizes = prizes.select_related('startrun', 'endrun', 'category').prefetch_related(
        'prizewinner_set'
    )
    return views_common.tracker_response(
        request, 'tracker/prizeindex.html', {'prizes': prizes, 'event': event},
    )


@cache_page(1800)
def prize_detail(request, pk):
    try:
        prize = Prize.objects.get(pk=pk)
        event = prize.event
        games = None
        category = None

        if prize.startrun:
            games = SpeedRun.objects.filter(
                starttime__gte=SpeedRun.objects.get(pk=prize.startrun.id).starttime,
                endtime__lte=SpeedRun.objects.get(pk=prize.endrun.id).endtime,
            )

        if prize.category:
            category = PrizeCategory.objects.get(pk=prize.category.id)

        return views_common.tracker_response(
            request,
            'tracker/prize.html',
            {'event': event, 'prize': prize, 'games': games, 'category': category},
        )
    except Prize.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


def websocket_test(request):
    if not settings.DEBUG:
        raise Http404
    socket_url = (
        request.build_absolute_uri(f'{reverse("tracker:index_all")}ws/ping/')
        .replace('https:', 'wss:')
        .replace('http:', 'ws:')
    )
    return views_common.tracker_response(
        request, 'tracker/websocket.html', {'socket_url': socket_url}
    )
