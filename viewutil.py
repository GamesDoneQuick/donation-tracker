import operator
import re
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Count, Sum, Max, Avg, Q
from django.db.models.functions import Coalesce
from django.http import Http404

from . import filters
from tracker.models import Donor, Event, Log
from functools import reduce


def get_default_email_host_user():
    return getattr(settings, 'EMAIL_HOST_USER', '')


def get_default_email_from_user():
    return getattr(settings, 'EMAIL_FROM_USER', get_default_email_host_user())


def admin_url(obj):
    return reverse(
        'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.object_name.lower()),
        args=(obj.pk,),
        current_app=obj._meta.app_label,
    )


# Adapted from http://djangosnippets.org/snippets/1474/
# TODO: use request.build_absolute_uri instead


def get_request_server_url(request):
    if request:
        return request.build_absolute_uri('/')
    else:
        raise Exception('Request was null.')


def get_referer_site(request):
    origin = request.META.get('HTTP_ORIGIN', None)
    if origin is not None:
        return re.sub(r'^https?:\/\/', '', origin)
    else:
        return None


def get_event(event):
    if event:
        if isinstance(event, Event):
            return event
        try:
            if re.match(r'^\d+$', event):
                return Event.objects.get(id=event)
            else:
                return Event.objects.get(short=event)
        except Event.DoesNotExist:
            raise Http404
    e = Event()
    e.id = None
    e.name = 'All Events'
    return e


def request_params(request):
    if request.method == 'GET':
        return request.GET
    elif request.method == 'POST':
        return request.POST
    else:
        raise Exception('No request parameters associated with this request method.')


_1ToManyBidsAggregateFilter = Q(bids__donation__transactionstate='COMPLETED')
_1ToManyDonationAggregateFilter = Q(donation__transactionstate='COMPLETED')
DonationBidAggregateFilter = _1ToManyDonationAggregateFilter
DonorAggregateFilter = _1ToManyDonationAggregateFilter
EventAggregateFilter = _1ToManyDonationAggregateFilter
PrizeWinnersFilter = Q(prizewinner__acceptcount_gt=0) | Q(
    prizewinner__pendingcount__gt=0
)

# http://stackoverflow.com/questions/5722767/django-mptt-get-descendants-for-a-list-of-nodes


def get_tree_queryset_descendants(model, nodes, include_self=False):
    if not nodes:
        return nodes
    filters = []
    for n in nodes:
        lft, rght = n.lft, n.rght
        if include_self:
            lft -= 1
            rght += 1
        filters.append(Q(tree_id=n.tree_id, lft__gt=lft, rght__lt=rght))
    q = reduce(operator.or_, filters)
    return model.objects.filter(q).order_by(*model._meta.ordering)


# http://stackoverflow.com/questions/6471354/efficient-function-to-retrieve-a-queryset-of-ancestors-of-an-mptt-queryset


def get_tree_queryset_ancestors(model, nodes):
    tree_list = {}
    query = Q()
    for node in nodes:
        if node.tree_id not in tree_list:
            tree_list[node.tree_id] = []
        parent = (node.parent.pk if node.parent is not None else None,)
        if parent not in tree_list[node.tree_id]:
            tree_list[node.tree_id].append(parent)
            query |= Q(lft__lt=node.lft, rght__gt=node.rght, tree_id=node.tree_id)
        return model.objects.filter(query).order_by(*model._meta.ordering)


def get_tree_queryset_all(model, nodes):
    filters = []
    for node in nodes:
        filters.append(Q(tree_id=node.tree_id))
    q = reduce(operator.or_, filters)
    return model.objects.filter(q).order_by(*model._meta.ordering)


ModelAnnotations = {
    'event': {
        'amount': Coalesce(
            Sum('donation__amount', only=EventAggregateFilter), Decimal('0.00')
        ),
        'count': Count('donation', only=EventAggregateFilter),
        'max': Coalesce(
            Max('donation__amount', only=EventAggregateFilter), Decimal('0.00')
        ),
        'avg': Coalesce(
            Avg('donation__amount', only=EventAggregateFilter), Decimal('0.00')
        ),
    },
    'prize': {'numwinners': Count('prizewinner', only=PrizeWinnersFilter),},
}


def find_people(people_list):
    result = []
    for person in people_list:
        try:
            d = Donor.objects.get(alias__iequals=person)
            result.append(d)
        except Exception:
            pass
    return result


def cmp(x, y):
    return (x > y) - (x < y)


def prizecmp(a, b):
    # if both prizes are run-linked, sort them that way
    if a.startrun and b.startrun:
        return (
            cmp(a.startrun.starttime, b.startrun.starttime)
            or cmp(a.endrun.endtime, b.endrun.endtime)
            or cmp(a.name, b.name)
        )
    # else if they're both time-linked, sort them that way
    if a.starttime and b.starttime:
        return (
            cmp(a.starttime, b.starttime)
            or cmp(a.endtime, b.endtime)
            or cmp(a.name, b.name)
        )
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
    return cmp(a.category, b.category) or cmp(a.name, b.name)


EVENT_SELECT = 'admin-event'


def get_selected_event(request):
    evId = request.session.get(EVENT_SELECT, None)
    if evId:
        return Event.objects.get(pk=evId)
    else:
        return None


def set_selected_event(request, event):
    if event:
        request.session[EVENT_SELECT] = event.id
    else:
        request.session[EVENT_SELECT] = None


def get_donation_prize_contribution(prize, donation, secondaryAmount=None):
    if prize.contains_draw_time(donation.timereceived):
        amount = secondaryAmount if secondaryAmount is not None else donation.amount
        if prize.sumdonations or amount >= prize.minimumbid:
            return amount
    return None


def get_donation_prize_info(donation):
    """ Attempts to find a list of all prizes this donation gives the donor eligibility for.
      Does _not_ attempt to relate this information to any _past_ eligibility.
      Returns the set as a list of {'prize','amount'} dictionaries. """
    prizeList = []
    for timeprize in filters.run_model_query(
        'prize',
        params={'feed': 'current', 'time': donation.timereceived, 'noslice': True,},
    ):
        contribAmount = get_donation_prize_contribution(timeprize, donation)
        if contribAmount is not None:
            prizeList.append({'prize': timeprize, 'amount': contribAmount})
    return prizeList


def tracker_log(category, message='', event=None, user=None):
    Log.objects.create(category=category, message=message, event=event, user=user)


def merge_bids(rootBid, bids):
    for bid in bids:
        if bid != rootBid:
            for donationBid in bid.bids.all():
                donationBid.bid = rootBid
                donationBid.save()
            for suggestion in bid.suggestions.all():
                suggestion.bid = rootBid
                suggestion.save()
            bid.delete()
    rootBid.save()
    return rootBid


def merge_donors(rootDonor, donors):
    for other in donors:
        if other != rootDonor:
            for donation in other.donation_set.all():
                donation.donor = rootDonor
                donation.save()
            for prizewin in other.prizewinner_set.all():
                prizewin.winner = rootDonor
                prizewin.save()
            other.delete()
    rootDonor.save()
    return rootDonor


def autocreate_donor_user(donor):
    AuthUser = get_user_model()

    if not donor.user:
        with transaction.atomic():
            try:
                linkUser = AuthUser.objects.get(email=donor.email)
            except AuthUser.MultipleObjectsReturned:
                message = 'Multiple users found for email {0}, when trying to mail donor {1} for prizes'.format(
                    donor.email, donor.id
                )
                tracker_log('prize', message)
                raise Exception(message)
            except AuthUser.DoesNotExist:
                targetUsername = donor.email
                if donor.alias and not AuthUser.objects.filter(username=donor.alias):
                    targetUsername = donor.alias
                linkUser = AuthUser.objects.create(
                    username=targetUsername,
                    email=donor.email,
                    first_name=donor.firstname,
                    last_name=donor.lastname,
                    is_active=False,
                )
            donor.user = linkUser
            donor.save()

    return donor.user
