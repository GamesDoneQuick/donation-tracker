import json
import traceback
import urllib.request

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core import serializers
from django.db.models import Sum

import tracker.models as models
import tracker.search_filters as filters
import tracker.viewutil as viewutil
from tracker.consumers.processing import broadcast_new_donation_to_processors

# TODO: this is 2018, we ought to be using requests


def post_donation_to_postbacks(donation):
    event_donations = filters.run_model_query('donation', {'event': donation.event.id})
    total = event_donations.aggregate(amount=Sum('amount'))['amount']

    data = {
        'id': donation.id,
        'event': donation.event_id,
        'timereceived': str(donation.timereceived),
        'comment': donation.comment,
        'amount': float(donation.amount),
        'donor__visibility': donation.donor.visibility,
        'donor__visiblename': donation.donor.visible_name(),
        'new_total': float(total),
        'domain': donation.domain,
        'bids': [
            {
                'pk': db.bid.pk,
                'id': db.bid.id,
                'total': float(db.bid.total),
                'parent': db.bid.parent_id,
                'name': db.bid.name,
                'goal': float(db.bid.goal) if db.bid.goal else None,
                'state': db.bid.state,
                'speedrun': db.bid.speedrun_id,
            }
            for db in donation.bids.select_related('bid')
        ],
    }

    async_to_sync(get_channel_layer().group_send)(
        'donations', {'type': 'donation', **data}
    )

    broadcast_new_donation_to_processors(donation)

    try:
        data_json = json.dumps(
            data, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder
        ).encode('utf-8')

        postbacks = models.PostbackURL.objects.filter(event=donation.event)
        for postback in postbacks:
            opener = urllib.request.build_opener()
            req = urllib.request.Request(
                postback.url,
                data_json,
                headers={'Content-Type': 'application/json; charset=utf-8'},
            )
            opener.open(req, timeout=5)
    except Exception:
        viewutil.tracker_log(
            'postback_url', traceback.format_exc(), event=donation.event
        )
