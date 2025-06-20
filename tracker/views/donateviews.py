import logging

from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from tracker import models, viewutil

from . import common as views_common

__all__ = [
    'paypal_cancel',
    'paypal_return',
    'donate',
]

logger = logging.getLogger(__name__)


@csrf_exempt
def paypal_cancel(request):
    return views_common.tracker_response(request, 'tracker/paypal_cancel.html')


@csrf_exempt
def paypal_return(request):
    return views_common.tracker_response(request, 'tracker/paypal_return.html')


@csrf_exempt
@cache_page(300)
def donate(request, event):
    event = viewutil.get_event(event)
    if not event.allow_donations:
        raise Http404
    return HttpResponsePermanentRedirect(reverse('tracker:ui:donate', args=(event.id,)))


def donate_current(request):
    event = models.Event.objects.current_or_next()

    if event:
        return HttpResponseRedirect(reverse('tracker:ui:donate', args=(event.id,)))

    raise Http404
