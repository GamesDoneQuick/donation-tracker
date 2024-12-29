# coding: utf-8

import datetime
import json
from decimal import Decimal

import responses
from django.test import TransactionTestCase

from tracker import eventutil
from tracker.models import Donation, Donor, Event, PostbackURL


class TestPostDonation(TransactionTestCase):
    def setUp(self):
        self.donor = Donor.objects.create()
        self.event = Event.objects.create(
            receivername='Médecins Sans Frontières',
            paypalemail='msf@example.com',
            paypalcurrency='USD',
            datetime=datetime.datetime(2018, 1, 1),
        )
        self.postback = PostbackURL.objects.create(
            event=self.event,
            url='https://example.com',
        )

    @responses.activate
    def test_request_made(self):
        responses.post('https://example.com', status=200)

        donation = Donation.objects.create(
            timereceived=datetime.datetime(2018, 1, 1),
            comment='',
            amount=Decimal(1.5),
            domain='PAYPAL',
            donor=self.donor,
            event=self.event,
            transactionstate='COMPLETED',
        )

        eventutil.post_donation_to_postbacks(donation)

        assert len(responses.calls) == 1
        resp = responses.calls[0]
        assert resp.request.url == 'https://example.com/'
        assert json.loads(resp.request.body) == {
            'id': donation.id,
            'event': donation.event_id,
            'timereceived': donation.timereceived.astimezone(
                donation.event.timezone
            ).isoformat(),
            'comment': '',
            'amount': 1.5,
            'donor__visibility': 'FIRST',
            'donor__visiblename': '(No Name)',
            'new_total': 1.5,
            'domain': 'PAYPAL',
            'bids': [],
        }
        assert resp.response.status_code == 200
