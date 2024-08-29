import json

import django.core.paginator as paginator
from django.db.models import Avg, Count, FloatField, Max, Sum
from django.db.models.functions import Cast, Coalesce
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.cache import cache_page

from tracker import search_filters as filters
from tracker import settings, util, viewutil
from tracker.models import (
    Bid,
    Donation,
    DonationBid,
    DonorCache,
    Milestone,
    Prize,
    PrizeCategory,
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
        request,
        'tracker/eventlist.html',
        {'pattern': 'tracker:index', 'show_all': True},
    )


def index(request, event=None):
    event = viewutil.get_event(event)
    eventParams = {}

    if event.id:
        eventParams['event'] = event.id

    donations = Donation.objects.filter(
        transactionstate='COMPLETED', testdonation=False, **eventParams
    )

    agg = donations.aggregate(
        total=Cast(Coalesce(Sum('amount'), 0), output_field=FloatField()),
        count=Count('amount'),
        max=Cast(Coalesce(Max('amount'), 0), output_field=FloatField()),
        avg=Cast(Coalesce(Avg('amount'), 0), output_field=FloatField()),
    )
    agg['median'] = float(util.median(donations, 'amount'))
    if event.targetamount:
        agg['target'] = float(event.targetamount)
    count = {
        'runs': filters.run_model_query('run', eventParams).count(),
        'prizes': filters.run_model_query('prize', eventParams).count(),
        'bids': filters.run_model_query('bid', eventParams).count(),
        'milestones': filters.run_model_query('milestone', eventParams).count(),
        # 'donors': filters.run_model_query('donorcache', eventParams)
        # .values('donor')
        # .distinct()
        # .count(),
    }

    if 'json' in request.GET:
        agg['amount'] = agg['total']  # api compatibility
        del agg['total']
        return HttpResponse(
            json.dumps(
                {'count': count, 'agg': agg},
                ensure_ascii=False,
            ),
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


def get_bid_steps(bid, bids):
    step = next((step for step in bids if step.parent_id == bid.id), None)
    if step:
        return [step] + get_bid_steps(step, bids)
    else:
        return []


def get_bid_ancestors(bid, bids):
    parent = bid
    while parent:
        parent = next((b for b in bids if parent.parent_id == b.id), None)
        if parent:
            yield parent


def get_bid_info(bid, bids):
    info = {
        'id': bid.id,
        'name': bid.name,
        'parent': bid.parent_name,
        'speedrun': bid.speedrun_name,
        'event': bid.event_name if not bid.speedrun_name else '',
        'description': bid.description,
        'goal': bid.goal,
        'total': bid.total,
        'istarget': bid.istarget,
        'chain': bid.chain,
    }
    if bid.goal:
        info['remaining'] = max(0, bid.goal - bid.total)
    if bid.chain:
        info['chain_total'] = min(bid.goal, bid.total)
        info['full_chain'] = bid.chain_goal + bid.chain_remaining
        info['chain_goal'] = bid.chain_goal
        info['chain_remaining'] = bid.chain_remaining
        if bid.istarget:
            info['steps'] = [
                get_bid_info(step, bids) for step in get_bid_steps(bid, bids)
            ]
    else:
        info['children'] = get_bid_children(bid, bids)
    return info


@cache_page(60)
@no_querystring
def bidindex(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return views_common.tracker_response(
            request,
            'tracker/eventlist.html',
            {'pattern': 'tracker:bidindex', 'subheading': 'Bids'},
        )

    bids = Bid.objects.public().filter(event=event).with_annotations()

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
            Bid.objects.public()
            .filter(pk=pk)
            .select_related('event')
            .with_annotations()
            .first()
        )
        if not bid:
            raise Bid.DoesNotExist
        if bid.chain and bid.parent_id:
            return HttpResponseRedirect(
                reverse('tracker:bid', args=(bid.get_root().id,))
            )
        bid_info = get_bid_info(
            bid,
            (bid.get_ancestors() | bid.get_descendants())
            .filter(state__in=('OPENED', 'CLOSED'))
            .with_annotations(),
        )

        page = request.GET.get('page', 1)
        page_info = page_or_404(
            bid.bids.completed()
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
@no_querystring
def milestoneindex(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return views_common.tracker_response(
            request,
            'tracker/eventlist.html',
            {'pattern': 'tracker:milestoneindex', 'subheading': 'Milestones'},
        )

    milestones = Milestone.objects.filter(event=event, visible=True)

    return views_common.tracker_response(
        request,
        'tracker/milestoneindex.html',
        {
            'milestones': milestones,
            'event': event,
        },
    )


@cache_page(60)
def donorindex(request, event=None):
    raise Http404
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
    agg = donors.aggregate(
        max=Cast(Coalesce(Max('donation_total'), 0), output_field=FloatField()),
        avg=Cast(Coalesce(Avg('donation_total'), 0), output_field=FloatField()),
    )
    agg['median'] = util.median(donors, 'donation_total')

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
            'agg': agg,
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
    raise Http404
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
        total=Sum('amount'),
        count=Count('amount'),
        max=Max('amount'),
        avg=Avg('amount'),
    )
    agg['median'] = util.median(donations, 'amount')
    donations = donations.select_related('donor')
    pages = paginator.Paginator(donations, 50)
    # TODO: these should really be errors
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
        return views_common.tracker_response(
            request,
            'tracker/eventlist.html',
            {'pattern': 'tracker:runindex', 'subheading': 'Runs'},
        )

    searchParams = {}
    searchParams['event'] = event.id

    runs = filters.run_model_query('run', searchParams)
    runs = runs.annotate(hasbids=Sum('bids'))
    # noinspection PyProtectedMember
    runs = runs.order_by(
        *SpeedRun._meta.ordering
    )  # Django 3.x erases the default ordering after an annotate

    return views_common.tracker_response(
        request,
        'tracker/runindex.html',
        {'runs': runs, 'event': event},
    )


@cache_page(300)
def run_detail(request, pk):
    try:
        run = SpeedRun.objects.get(pk=pk)
        runners = run.runners.all()
        event = run.event
        bids = Bid.objects.public().filter(speedrun=pk).with_annotations()
        bids = [get_bid_info(bid, bids) for bid in bids.filter(level=0)]

        return views_common.tracker_response(
            request,
            'tracker/run.html',
            {'event': event, 'run': run, 'runners': runners, 'bids': bids},
        )

    except SpeedRun.DoesNotExist:
        return views_common.tracker_response(
            request, template='tracker/badobject.html', status=404
        )


@cache_page(60)
def prizeindex(request, event=None):
    if not settings.TRACKER_SWEEPSTAKES_URL:
        raise Http404

    event = viewutil.get_event(event)

    if not event.id:
        return views_common.tracker_response(
            request,
            'tracker/eventlist.html',
            {'pattern': 'tracker:prizeindex', 'subheading': 'Prizes'},
        )

    searchParams = {}
    searchParams['event'] = event.id

    prizes = filters.run_model_query('prize', searchParams)
    prizes = prizes.select_related('startrun', 'endrun', 'category').prefetch_related(
        'prizewinner_set'
    )
    return views_common.tracker_response(
        request,
        'tracker/prizeindex.html',
        {'prizes': prizes, 'event': event},
    )


@cache_page(60)
def prize_detail(request, pk):
    if not settings.TRACKER_SWEEPSTAKES_URL:
        raise Http404
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
