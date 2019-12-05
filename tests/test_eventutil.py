# coding: utf-8

import datetime
from decimal import Decimal
from unittest import skip

import responses
from django.test import TransactionTestCase

from tracker import eventutil
from tracker.models import Donation, Donor, Event, PostbackURL


class TestPostDonation(TransactionTestCase):
    def setUp(self):
        self.donor = Donor.objects.create()
        self.event = Event.objects.create(
            receivername='Médecins Sans Frontières',
            targetamount=1,
            paypalemail='msf@example.com',
            paypalcurrency='USD',
            datetime=datetime.datetime(2018, 1, 1),
        )
        self.postback = PostbackURL.objects.create(
            event=self.event, url='https://example.com'
        )

    @skip("This test only works with requests :')")
    @responses.activate
    def test_request_made(self):
        responses.add(responses.GET, 'https://example.com', status=200)

        donation = Donation.objects.create(
            timereceived=datetime.datetime(2018, 1, 1),
            comment='',
            amount=Decimal(1.5),
            domain='PAYPAL',
            donor=self.donor,
            event=self.event,
        )

        eventutil.post_donation_to_postbacks(donation)

        assert len(responses.calls) == 1
        assert (
            responses.calls[0].request.url
            == 'https://example.com/?comment=&amount=1.5&timereceived=2018-01-01+00%3A00%3A00&donor__visibility=FIRST&domain=PAYPAL&id=1&donor__visiblename=%28No+Name%29'
        )
        assert responses.calls[0].response.status_code == 200
