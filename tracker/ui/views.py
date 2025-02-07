import json
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import AnonymousUser
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.csrf import csrf_protect

from tracker import search_filters, settings, viewutil
from tracker.decorators import no_querystring
from tracker.models import Event
from tracker.views.donateviews import process_form


def constants(user=None):
    user = user or AnonymousUser
    return {
        'PRIVACY_POLICY_URL': settings.TRACKER_PRIVACY_POLICY_URL,
        'SWEEPSTAKES_URL': settings.TRACKER_SWEEPSTAKES_URL,
        'ANALYTICS_URL': reverse('tracker:analytics'),
        'API_ROOT': reverse('tracker:api_v1:root'),
        'APIV2_ROOT': reverse('tracker:api_v2:api-root'),
        'ADMIN_ROOT': (
            reverse('admin:app_list', kwargs={'app_label': 'tracker'})
            if user.is_staff
            else ''
        ),
        'STATIC_URL': settings.STATIC_URL,
        'PAGINATION_LIMIT': settings.TRACKER_PAGINATION_LIMIT,
    }


@csrf_protect
@cache_page(60)
@no_querystring
def index(request, **kwargs):
    return render(
        request,
        'ui/generated/tracker.html',
        {
            'event': Event.objects.current(),
            'events': Event.objects.all(),
            'CONSTANTS': constants(),
            'ROOT_PATH': reverse('tracker:ui:index'),
            'app_name': 'TrackerApp',
            'form_errors': {},
            'props': {},
        },
    )


@never_cache
@staff_member_required
def admin_redirect(request, extra):
    return HttpResponsePermanentRedirect(
        reverse('admin:tracker_ui', kwargs=dict(extra=extra))
    )


@csrf_protect
@no_querystring
def donate(request, event):
    event = viewutil.get_event(event)
    if event.locked or not event.allow_donations:
        raise Http404

    commentform, bidsform = process_form(request, event)

    if not bidsform:  # redirect
        return commentform

    def bid_parent_info(bid):
        if bid is not None:
            return {
                'id': bid.id,
                'name': bid.name,
                'description': bid.description,
                'parent': bid_parent_info(bid.parent),
                'custom': bid.allowuseroptions,
            }
        else:
            return None

    def bid_info(bid):
        result = {
            'id': bid.id,
            'name': bid.name,
            'description': bid.description,
            'label': bid.full_label(not bid.allowuseroptions),
            'count': bid.count,
            'amount': bid.total,
            'goal': Decimal(bid.goal or '0.00'),
            'parent': bid_parent_info(bid.parent),
        }
        if bid.speedrun:
            result['runname'] = bid.speedrun.name
            result['order'] = bid.speedrun.order
        else:
            result['runname'] = 'Event Wide'
            result['order'] = 0
        if not (bid.istarget or bid.chain):
            result['accepted_number'] = bid.accepted_number
        if bid.allowuseroptions:
            result['custom'] = True
            result['maxlength'] = bid.option_max_length
        return result

    bids = search_filters.run_model_query(
        'allbids', {'state': 'OPENED', 'event': event.id}
    ).select_related('parent', 'speedrun')

    prizes = search_filters.run_model_query(
        'prize', {'feed': 'current', 'event': event.id}
    )

    # You have to try really hard to get into this state so it's reasonable to blow up spectacularly when it happens
    if prizes and not settings.TRACKER_SWEEPSTAKES_URL:
        raise ImproperlyConfigured(
            'There are prizes available but no TRACKER_SWEEPSTAKES_URL is set'
        )

    bidsArray = [bid_info(o) for o in bids]

    def prize_info(prize):
        result = {
            'id': prize.id,
            'name': prize.name,
            'description': prize.description,
            'minimumbid': prize.minimumbid,
            'sumdonations': prize.sumdonations,
            'url': reverse('tracker:prize', args=(prize.id,)),
            'image': prize.image,
        }
        return result

    prizesArray = [prize_info(o) for o in prizes.all()]

    def to_json(value):
        if hasattr(value, 'id'):
            return value.id
        return value

    initialForm = {
        k: to_json(commentform.cleaned_data[k])
        for k, v in commentform.fields.items()
        if commentform.is_bound and k in commentform.cleaned_data
    }
    pickedIncentives = [
        {
            k: to_json(form.cleaned_data[k])
            for k, v in form.fields.items()
            if k in form.cleaned_data
        }
        for form in bidsform.forms
        if form.is_bound
    ]

    return render(
        request,
        'ui/generated/tracker.html',
        {
            'event': event,
            'events': Event.objects.all(),
            'CONSTANTS': constants(),
            'ROOT_PATH': reverse('tracker:ui:index'),
            'app_name': 'TrackerApp',
            'title': 'Donation Tracker',
            'forms': {'bidsform': bidsform},
            'form_errors': {
                'commentform': json.loads(commentform.errors.as_json()),
                'bidsform': bidsform.errors,
            },
            'props': {
                'event': json.loads(serializers.serialize('json', [event]))[0][
                    'fields'
                ],
                'minimumDonation': float(event.minimumdonation),
                'prizes': prizesArray,
                'incentives': bidsArray,
                'initialForm': initialForm,
                'initialIncentives': pickedIncentives,
                'donateUrl': request.get_full_path(),
                'prizesUrl': request.build_absolute_uri(
                    reverse('tracker:prizeindex', args=(event.id,))
                ),
            },
        },
    )
