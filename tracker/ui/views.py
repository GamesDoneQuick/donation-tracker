import contextlib

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import NoReverseMatch
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework.request import Request

from tracker import settings, viewutil
from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import BidSerializer, EventSerializer, PrizeSerializer
from tracker.compat import reverse
from tracker.decorators import no_querystring
from tracker.models import Bid, Event, Prize


def constants(user=None):
    user = user or AnonymousUser
    extra = {}
    if user.is_staff:
        # admin app might not be installed on this site
        with contextlib.suppress(NoReverseMatch):
            extra['ADMIN_ROOT'] = reverse(
                'admin:app_list', kwargs={'app_label': 'tracker'}
            )

    return {
        'PRIVACY_POLICY_URL': settings.TRACKER_PRIVACY_POLICY_URL,
        'SWEEPSTAKES_URL': settings.TRACKER_SWEEPSTAKES_URL,
        'ANALYTICS_URL': reverse('tracker:analytics'),
        'APIV2_ROOT': reverse('tracker:api_v2:api-root'),
        'STATIC_URL': settings.STATIC_URL,
        'PAGINATION_LIMIT': settings.TRACKER_PAGINATION_LIMIT,
        'PAYPAL_MAXIMUM_AMOUNT': settings.TRACKER_PAYPAL_MAXIMUM_AMOUNT,
        **extra,
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
            'CONSTANTS': {
                **constants(),
                'ROOT_PATH': reverse('tracker:ui:index'),
            },
            'app_name': 'TrackerApp',
            'settings': {
                'TRACKER_SWEEPSTAKES_URL': settings.TRACKER_SWEEPSTAKES_URL,
                'TRACKER_LOGO': settings.TRACKER_LOGO,
                'TRACKER_CONTRIBUTORS_URL': settings.TRACKER_CONTRIBUTORS_URL,
            },
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

    prefetch = cache.get(f'event_prefetch_{event.id}')

    if prefetch is None:
        drf_request = Request(request)

        paginator = TrackerPagination()
        events = paginator.get_paginated_response(
            EventSerializer(
                paginator.paginate_queryset(
                    Event.objects.filter(allow_donations=True),
                    drf_request,
                ),
                many=True,
            ).data
        ).data
        prizes = paginator.get_paginated_response(
            PrizeSerializer(
                paginator.paginate_queryset(
                    Prize.objects.current().filter(event=event), drf_request
                ),
                event_pk=event.pk,
                many=True,
            ).data
        ).data

        # You have to try really hard to get into this state so it's reasonable to blow up spectacularly when it happens
        if prizes['count'] and not settings.TRACKER_SWEEPSTAKES_URL:
            raise ImproperlyConfigured(
                'There are prizes available but no TRACKER_SWEEPSTAKES_URL is set'
            )

        bids = paginator.get_paginated_response(
            BidSerializer(
                paginator.paginate_queryset(
                    Bid.objects.open().filter(event=event, level=0), drf_request
                ),
                many=True,
                tree=True,
            ).data
        ).data
        prefetch = {
            reverse('tracker:api_v2:event-list'): events,
            reverse(
                'tracker:api_v2:event-prize-feed-list',
                kwargs={'event_pk': event.id, 'feed': 'current'},
            ): prizes,
            reverse(
                'tracker:api_v2:event-bid-feed-tree',
                kwargs={'event_pk': event.id, 'feed': 'open'},
            ): bids,
        }
        cache.set(f'event_prefetch_{event.id}', prefetch, 300)

    return render(
        request,
        'ui/generated/tracker.html',
        {
            'event': event,
            'events': Event.objects.all(),
            'CONSTANTS': {
                **constants(),
                'ROOT_PATH': reverse('tracker:ui:index'),
            },
            'app_name': 'TrackerApp',
            'API_PREFETCH': prefetch,
            'title': 'Donation Tracker',
            'settings': {
                'TRACKER_SWEEPSTAKES_URL': settings.TRACKER_SWEEPSTAKES_URL,
                'TRACKER_LOGO': settings.TRACKER_LOGO,
                'TRACKER_CONTRIBUTORS_URL': settings.TRACKER_CONTRIBUTORS_URL,
            },
        },
    )
