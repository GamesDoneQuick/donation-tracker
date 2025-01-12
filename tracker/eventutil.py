import json
import logging
import traceback

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core import serializers
from django.db.models import Sum

import tracker.models as models
import tracker.search_filters as filters
import tracker.viewutil as viewutil
from tracker.api.serializers import BidSerializer
from tracker.consumers.processing import broadcast_new_donation_to_processors

logger = logging.getLogger(__name__)


def _bid_info(bid):
    return {**BidSerializer(bid, tree=True).data, 'pk': bid.id}


def post_donation_to_postbacks(donation):
    event_donations = filters.run_model_query('donation', {'event': donation.event.id})
    total = event_donations.aggregate(amount=Sum('amount'))['amount']
    donation_count = event_donations.count()

    data = {
        'id': donation.id,
        'event': donation.event_id,
        'timereceived': donation.timereceived.astimezone(
            donation.event.timezone
        ).isoformat(),
        'comment': donation.comment,
        'amount': float(donation.amount),
        # FIXME: only happens in tests
        'donor__visibility': donation.donor and donation.donor.visibility,
        'donor__visiblename': donation.donor and donation.donor.visible_name(),
        'new_total': float(total),
        'domain': donation.domain,
        'bids': [
            _bid_info(db.bid)
            for db in donation.bids.filter(
                bid__state__in=models.Bid.PUBLIC_STATES
            ).select_related('bid')
        ],
    }

    async_to_sync(get_channel_layer().group_send)(
        'donations', {'type': 'donation', **data}
    )

    broadcast_new_donation_to_processors(donation, float(total), donation_count)

    try:
        data_json = json.dumps(
            data, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder
        ).encode('utf-8')

        postbacks = models.PostbackURL.objects.filter(event=donation.event)
        for postback in postbacks:
            requests.post(
                postback.url,
                data=data_json,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=5,
            )
    except Exception:
        logger.exception('Error sending postback')
        viewutil.tracker_log(
            'postback_url', traceback.format_exc(), event=donation.event
        )
