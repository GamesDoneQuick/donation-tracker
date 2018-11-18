import json
import os
from decimal import Decimal

from django.conf import settings
from django.core import serializers
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from webpack_manifest import webpack_manifest

from tracker import filters, viewutil
from tracker.models import Event
from tracker.views.donateviews import process_form


@csrf_protect
def index(request):
    raise Http404  # nothing yet
    bundle = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-tracker.manifest.json')),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    return render(
        request,
        'tracker_ui/index.html',
        dictionary={
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.index,
            'root_path': reverse('tracker_ui:index'),
            'app': 'IndexApp',
            'props': mark_safe(json.dumps({}, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder)),
        },
    )


@csrf_protect
def admin(request):
    bundle = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-tracker.manifest.json')),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    return render(
        request,
        'tracker_ui/index.html',
        dictionary={
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.admin,
            'root_path': reverse('tracker_ui:admin'),
            'app': 'AdminApp',
            'form_errors': {},
            'props': mark_safe(json.dumps({}, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder)),
        },
    )


@csrf_protect
def donate(request, event):
    event = viewutil.get_event(event)
    if event.locked:
        raise Http404

    bundle = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-tracker.manifest.json')),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    commentform, bidsform, prizesform = process_form(request, event)

    if not bidsform:
        return commentform

    def bid_parent_info(bid):
        if bid != None:
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
            'parent': bid_parent_info(bid.parent)
        }
        if bid.speedrun:
            result['runname'] = bid.speedrun.name
        else:
            result['runname'] = 'Event Wide'
        if bid.allowuseroptions:
            result['custom'] = True
        return result

    bids = filters.run_model_query('bidtarget',
                                   {'state': 'OPENED', 'event': event.id},
                                   user=request.user) \
        .distinct().select_related('parent', 'speedrun').prefetch_related('suggestions')

    prizes = filters.run_model_query('prize', {'feed': 'current', 'event': event.id})

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

    initialForm = {k: to_json(commentform.cleaned_data[k]) for k, v in commentform.fields.items() if
                   commentform.is_bound and k in commentform.cleaned_data}
    pickedIncentives = [
        {k: to_json(form.cleaned_data[k]) for k, v in form.fields.items() if k in form.cleaned_data} for
        form in bidsform.forms if form.is_bound
    ]

    return render(
        request,
        'tracker_ui/index.html',
        dictionary={
            'event': event,
            'events': Event.objects.all(),
            'bundle': bundle.donate,
            'root_path': reverse('tracker_ui:index'),
            'app': 'DonateApp',
            'title': 'Donate',
            'forms': {'bidsform': bidsform, 'prizesform': prizesform},
            'form_errors': mark_safe(json.dumps({
                'commentform': json.loads(commentform.errors.as_json()),
                'bidsform': bidsform.errors,
            })),
            'props': mark_safe(json.dumps({
                'event': json.loads(serializers.serialize('json', [event]))[0]['fields'],
                'prizes': prizesArray,
                'incentives': bidsArray,
                'initialForm': initialForm,
                'initialIncentives': pickedIncentives,
                'donateUrl': request.get_full_path(),
                'prizesUrl': request.build_absolute_uri(reverse('tracker:prizeindex', args=(event.id,))),
                'rulesUrl': 'https://gamesdonequick.com/sweepstakes',  # TODO: put in settings?
            }, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder)),
        },
    )
