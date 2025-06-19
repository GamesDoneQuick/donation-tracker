import operator
import re
from functools import reduce

from django.db.models import Q
from django.http import Http404
from django.urls import reverse

from tracker.models import Event, Log


def admin_url(obj):
    return reverse(
        'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.object_name.lower()),
        args=(obj.pk,),
        current_app=obj._meta.app_label,
    )


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
    e = Event(name='All Events', allow_donations=False)
    return e


# http://stackoverflow.com/questions/5722767/django-mptt-get-descendants-for-a-list-of-nodes
# TODO: is this not just part of the queryset now?


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
# TODO: is this not just part of the queryset now?


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
            for claim in other.prizeclaims.all():
                claim.winner = rootDonor
                claim.save()
            other.delete()
    rootDonor.save()
    return rootDonor
