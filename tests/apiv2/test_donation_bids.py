from decimal import Decimal

from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import DonationBidSerializer


class TestDonationBids(APITestCase):
    model_name = 'donationbid'
    serializer_class = DonationBidSerializer
    extra_serializer_kwargs = {'with_permissions': 'tracker.view_bid'}
    view_user_permissions = ['view_bid']

    def _format_donation_bid(self, bid):
        bid.refresh_from_db()
        return {
            'type': 'donationbid',
            'id': bid.id,
            'donation': bid.donation_id,
            'bid': bid.bid_id,
            'bid_name': bid.bid.fullname(),
            'bid_state': bid.bid.state,
            'amount': bid.amount,
        }

    def setUp(self):
        super().setUp()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.donation = randgen.generate_donation(
            self.rand, min_amount=10, max_amount=25
        )
        self.donation.save()
        self.other_donation = randgen.generate_donation(self.rand)
        self.other_donation.save()
        self.pending_donation = randgen.generate_donation(
            self.rand, domain='PAYPAL', transactionstate='PENDING'
        )
        self.pending_donation.save()
        self.opened_bid = randgen.generate_bid(
            self.rand,
            event=self.event,
            state='OPENED',
            allow_children=True,
            allowuseroptions=True,
        )[0]
        self.opened_bid.save()
        self.opened_child = randgen.generate_bid(
            self.rand, parent=self.opened_bid, state='OPENED', allow_children=False
        )[0]
        self.opened_child.save()
        self.denied_child = randgen.generate_bid(
            self.rand, parent=self.opened_bid, state='DENIED', allow_children=False
        )[0]
        self.denied_child.save()
        self.opened_child_bid = models.DonationBid.objects.create(
            donation=self.donation,
            bid=self.opened_child,
            amount=Decimal(self.rand.uniform(5.0, 9.5)),
        )
        self.denied_child_bid = models.DonationBid.objects.create(
            donation=self.donation,
            bid=self.denied_child,
            amount=self.donation.amount - self.opened_child_bid.amount,
        )
        self.other_child_bid = models.DonationBid.objects.create(
            donation=self.other_donation,
            bid=self.opened_child,
            amount=self.other_donation.amount / 3,
        )
        self.hidden_bid, hidden_children = randgen.generate_bid(
            self.rand,
            event=self.event,
            min_children=1,
            max_children=1,
            state='HIDDEN',
            allow_children=True,
            allowuseroptions=True,
        )
        self.hidden_child = hidden_children[0][0]
        self.hidden_bid.save()
        self.hidden_child.save()
        self.hidden_denied_child = randgen.generate_bid(
            self.rand, parent=self.hidden_bid, state='DENIED', allow_children=False
        )[0]
        self.hidden_denied_child.save()
        self.hidden_child_bid = models.DonationBid.objects.create(
            donation=self.other_donation,
            bid=self.hidden_child,
            amount=self.other_donation.amount / 3,
        )
        self.hidden_denied_child_bid = models.DonationBid.objects.create(
            donation=self.other_donation,
            bid=self.hidden_denied_child,
            amount=self.other_donation.amount / 3,
        )
        self.pending_donation_bid = models.DonationBid.objects.create(
            donation=self.pending_donation,
            bid=self.opened_child,
            amount=self.pending_donation.amount,
        )

    def test_fetch(self):
        with self.saveSnapshot():
            with self.subTest('via donation'):
                data = self.get_noun(
                    'bids', self.donation, model_name='donation', user=self.view_user
                )
                self.assertExactV2Models([self.opened_child_bid], data)

                data = self.get_noun(
                    'bids',
                    self.donation,
                    data={'all': ''},
                    model_name='donation',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [self.opened_child_bid, self.denied_child_bid], data
                )

                data = self.get_noun(
                    'bids',
                    self.other_donation,
                    data={'all': ''},
                    model_name='donation',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [
                        self.other_child_bid,
                        self.hidden_child_bid,
                        self.hidden_denied_child_bid,
                    ],
                    data,
                )

            with self.subTest('via parent bid'):
                data = self.get_noun(
                    'donations',
                    self.opened_bid,
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [self.opened_child_bid, self.other_child_bid], data
                )

                data = self.get_noun(
                    'donations',
                    self.opened_bid,
                    data={'all': ''},
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [
                        self.opened_child_bid,
                        self.denied_child_bid,
                        self.other_child_bid,
                    ],
                    data,
                )

                data = self.get_noun(
                    'donations',
                    self.hidden_bid,
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [self.hidden_child_bid, self.hidden_denied_child_bid],
                    data,
                )

            with self.subTest('via child bid'):
                data = self.get_noun(
                    'donations',
                    self.opened_child,
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models(
                    [self.opened_child_bid, self.other_child_bid], data
                )

                data = self.get_noun(
                    'donations',
                    self.denied_child,
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models([self.denied_child_bid], data)

                data = self.get_noun(
                    'donations',
                    self.hidden_child,
                    model_name='bid',
                    user=self.view_user,
                )
                self.assertExactV2Models([self.hidden_child_bid], data)

        with self.subTest('error cases'):
            # strictly speaking, 403, but easier to write the permission check this way
            self.get_noun(
                'bids',
                self.donation,
                data={'all': ''},
                model_name='donation',
                user=None,
                status_code=404,
            )
            self.get_noun(
                'bids',
                self.pending_donation,
                model_name='donation',
                user=None,
                status_code=404,
            )
            self.get_noun(
                'donations',
                self.opened_bid,
                data={'all': ''},
                model_name='bid',
                user=None,
                status_code=404,
            )
            self.get_noun(
                'donations',
                self.denied_child,
                model_name='bid',
                user=None,
                status_code=404,
            )
            self.get_noun(
                'donations',
                self.hidden_bid,
                model_name='bid',
                user=None,
                status_code=404,
            )

    def test_serializer(self):
        with self.assertRaises(AssertionError):
            print(DonationBidSerializer(self.hidden_child_bid).data)

        data = DonationBidSerializer(
            self.hidden_child_bid, with_permissions=('tracker.view_bid')
        ).data
        self.assertEqual(data, self._format_donation_bid(self.hidden_child_bid))

        data = DonationBidSerializer(
            [self.opened_child_bid, self.other_child_bid], many=True
        ).data
        self.assertEqual(data[0], self._format_donation_bid(self.opened_child_bid))
        self.assertEqual(data[1], self._format_donation_bid(self.other_child_bid))
