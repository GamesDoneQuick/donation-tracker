import json
import traceback
import urllib.request

from django.core import serializers
from django.db.models import Sum

import tracker.filters as filters
import tracker.models as models
import tracker.viewutil as viewutil

# TODO: this is 2018, we ought to be using requests


def post_donation_to_postbacks(donation):
    event_donations = filters.run_model_query("donation", {"event": donation.event.id})
    total = event_donations.aggregate(amount=Sum("amount"))["amount"]

    data = {
        "id": donation.id,
        "timereceived": str(donation.timereceived),
        "comment": donation.comment,
        "amount": donation.amount,
        "donor__visibility": donation.donor.visibility,
        "donor__visiblename": donation.donor.visible_name(),
        "new_total": total,
        "domain": donation.domain,
    }

    # XXX: django/urllib2 throws UnicodeDecideError when payloads contain
    # unicode codepoints:
    #   UnicodeDecodeError: 'ascii' codec can't decode byte 0xc5 in position 292: ordinal not in range(128)
    try:
        data_json = json.dumps(
            data, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder
        ).encode("utf-8")

        postbacks = models.PostbackURL.objects.filter(event=donation.event)
        for postback in postbacks:
            opener = urllib.request.build_opener()
            req = urllib.request.Request(
                postback.url,
                data_json,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            opener.open(req, timeout=5)
    except Exception:
        viewutil.tracker_log(
            "postback_url", traceback.format_exc(), event=donation.event
        )
