import json
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import AnonymousUser
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.csrf import csrf_protect
from tracker.views import common as views_common
from webpack_manifest import webpack_manifest

from tracker import search_filters, viewutil
from tracker.decorators import no_querystring
from tracker.models import Event
from tracker.views.donateviews import process_form


def constants(user=None):
    user = user or AnonymousUser
    return {
        'PRIVACY_POLICY_URL': getattr(settings, 'PRIVACY_POLICY_URL', ''),
        'SWEEPSTAKES_URL': getattr(settings, 'SWEEPSTAKES_URL', ''),
        'API_ROOT': reverse('tracker:api_v1:root'),
        'ADMIN_ROOT': reverse('admin:app_list', kwargs={'app_label': 'tracker'})
        if user.is_staff
        else '',
        'STATIC_URL': settings.STATIC_URL,
    }


@csrf_protect
@cache_page(60)
@no_querystring
def index(request, **kwargs):
    bundle = webpack_manifest.load(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../ui-tracker.manifest.json')
        ),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None,
    )

    return render(
        request,
        'ui/index.html',
        {
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.tracker,
            'CONSTANTS': constants(),
            'ROOT_PATH': reverse('tracker:ui:index'),
            'app_name': 'TrackerApp',
            'form_errors': {},
            'props': {},
        },
    )


@csrf_protect
@never_cache
@no_querystring
@staff_member_required
def admin(request, ROOT_PATH=None, **kwargs):
    ROOT_PATH = ROOT_PATH or reverse('tracker:ui:admin')
    bundle = webpack_manifest.load(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../ui-tracker.manifest.json')
        ),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None,
    )

    return render(
        request,
        'ui/index.html',
        {
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.admin,
            'CONSTANTS': constants(request.user),
            'ROOT_PATH': ROOT_PATH,
            'app_name': 'AdminApp',
            'form_errors': {},
            'props': {},
        },
    )


@csrf_protect
@no_querystring
def donate(request, event):
    event = viewutil.get_event(event)
    if event.locked or not event.allow_donations:
        return views_common.tracker_response(request, 'tracker/donate_close.html')

    bundle = webpack_manifest.load(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../ui-tracker.manifest.json')
        ),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None,
    )

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
    if prizes and not getattr(settings, 'SWEEPSTAKES_URL', None):
        raise ImproperlyConfigured(
            'There are prizes available but no SWEEPSTAKES_URL is set'
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
        'ui/index.html',
        {
            'event': event,
            'events': Event.objects.all(),
            'bundle': bundle.tracker,
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
