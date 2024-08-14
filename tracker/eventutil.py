import json
import logging
import traceback

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core import serializers
from django.db.models import Count, Sum

import tracker.models as models
import tracker.viewutil as viewutil
from tracker.consumers.processing import broadcast_new_donation_to_processors

logger = logging.getLogger(__name__)


def post_donation_to_postbacks(donation):
    event_donations = models.Donation.objects.filter(event=donation.event).completed()
    agg = event_donations.aggregate(total=Sum('amount'), count=Count('amount'))
    total = agg['total']
    donation_count = agg['count']

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
            {
                'id': db.bid.id,
                'total': float(db.bid.total),
                'parent': db.bid.parent_id,
                'name': db.bid.name,
                'goal': float(db.bid.goal) if db.bid.goal else None,
                'state': db.bid.state,
                'speedrun': db.bid.speedrun_id,
            }
            for db in donation.bids.public().select_related('bid')
        ],
    }

    async_to_sync(get_channel_layer().group_send)(
        'donations', {'type': 'donation', **data}
    )

    broadcast_new_donation_to_processors(donation, float(total), donation_count)

    data_json = json.dumps(
        data, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder
    ).encode('utf-8')

    postbacks = models.PostbackURL.objects.filter(event=donation.event)
    for postback in postbacks:
        try:
            requests.post(
                postback.url,
                data=data_json,
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=5,
            )
        except Exception:
            logger.exception('Error sending postback')
            viewutil.tracker_log(
                'postback_url',
                f'{postback.id}\n{traceback.format_exc()}',
                event=donation.event,
            )
