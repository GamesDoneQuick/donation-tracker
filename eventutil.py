import json
import urllib2

from django.core import serializers
from django.db.models import Sum

import tracker.filters as filters
import tracker.models as models

def post_donation_to_postbacks(donation):
    event_donations = filters.run_model_query('donation',
                                              {'event': donation.event.id })
    total = event_donations.aggregate(amount=Sum('amount'))['amount']

    data = {
        'id': donation.id,
        'timereceived': str(donation.timereceived),
        'comment': donation.comment,
        'amount': donation.amount,
        'donor__visibility': donation.donor.visibility,
        'donor__visiblename': donation.donor.visible_name(),
        'new_total': total,
        'domain': donation.domain
    }
    data_json = json.dumps(data, ensure_ascii=False,
                           cls=serializers.json.DjangoJSONEncoder).encode('utf-8')

    postbacks = models.PostbackURL.objects.filter(event=donation.event)
    for postback in postbacks:
        opener = urllib2.build_opener()
        req = urllib2.Request(postback.url, data_json,
                              headers={'Content-Type': 'application/json; charset=utf-8'})
        response = opener.open(req, timeout=5)
