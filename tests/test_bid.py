import random

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from tracker import models
from .util import today_noon
from . import randgen


class TestBidBase(TestCase):
    def setUp(self):
        super(TestBidBase, self).setUp()
        self.rand = random.Random(None)
        self.event = models.Event.objects.create(
            datetime=today_noon, targetamount=5, short='test'
        )
        self.run = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='0:45:00',
            setup_time='0:05:00',
            order=1,
        )
        self.donor = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com'
        )
        self.donation = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=5, transactionstate='COMPLETED'
        )
        # TODO: a lot of the clean logic should actually be in save
        self.opened_parent_bid = models.Bid.objects.create(
            name='Opened Parent Test', speedrun=self.run, state='OPENED'
        )
        self.opened_parent_bid.clean()
        self.opened_parent_bid.save()
        self.closed_parent_bid = models.Bid.objects.create(
            name='Closed Parent Test', speedrun=self.run, state='CLOSED'
        )
        self.closed_parent_bid.clean()
        self.closed_parent_bid.save()
        self.opened_bid = models.Bid.objects.create(
            name='Opened Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='OPENED',
        )
        self.opened_bid.clean()
        self.opened_bid.save()
        # this one needs a different parent because of the way opened/closed interacts through the tree
        self.closed_bid = models.Bid.objects.create(
            name='Closed Test',
            istarget=True,
            parent=self.closed_parent_bid,
            state='CLOSED',
        )
        self.closed_bid.clean()
        self.closed_bid.save()
        self.hidden_bid = models.Bid.objects.create(
            name='Hidden Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='HIDDEN',
        )
        self.hidden_bid.clean()
        self.hidden_bid.save()
        self.denied_bid = models.Bid.objects.create(
            name='Denied Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='DENIED',
        )
        self.denied_bid.clean()
        self.denied_bid.save()
        self.pending_bid = models.Bid.objects.create(
            name='Pending Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='PENDING',
        )
        self.pending_bid.clean()
        self.pending_bid.save()


class TestBid(TestBidBase):
    def test_opened_bid(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.opened_bid, amount=self.donation.amount
        )
        self.opened_parent_bid.refresh_from_db()
        self.assertEqual(
            self.opened_bid.total, self.donation.amount, msg='opened bid total is wrong'
        )
        self.assertEqual(
            self.opened_parent_bid.total,
            self.donation.amount,
            msg='parent bid total is wrong',
        )

    def test_closed_bid(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.closed_bid, amount=self.donation.amount
        )
        self.closed_parent_bid.refresh_from_db()
        self.assertEqual(
            self.closed_bid.total, self.donation.amount, msg='closed bid total is wrong'
        )
        self.assertEqual(
            self.closed_parent_bid.total,
            self.donation.amount,
            msg='parent bid total is wrong',
        )

    def test_hidden_bid(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.hidden_bid, amount=self.donation.amount
        )
        self.opened_parent_bid.refresh_from_db()
        self.assertEqual(
            self.hidden_bid.total, self.donation.amount, msg='hidden bid total is wrong'
        )
        self.assertEqual(
            self.opened_parent_bid.total, 0, msg='parent bid total is wrong'
        )

    def test_denied_bid(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.denied_bid, amount=self.donation.amount
        )
        self.opened_parent_bid.refresh_from_db()
        self.assertEqual(
            self.denied_bid.total, self.donation.amount, msg='denied bid total is wrong'
        )
        self.assertEqual(
            self.opened_parent_bid.total, 0, msg='parent bid total is wrong'
        )

    def test_pending_bid(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.pending_bid, amount=self.donation.amount
        )
        self.opened_parent_bid.refresh_from_db()
        self.assertEqual(
            self.pending_bid.total,
            self.donation.amount,
            msg='pending bid total is wrong',
        )
        self.assertEqual(
            self.opened_parent_bid.total, 0, msg='parent bid total is wrong'
        )

    def test_bid_option_max_length_require(self):
        # A bid cannot set option_max_length if allowuseroptions is not set
        bid = models.Bid(name='I am a bid', option_max_length=1)
        with self.assertRaisesRegex(
            ValidationError, 'Cannot set option_max_length without allowuseroptions'
        ):
            bid.clean()

    def test_bid_suggestion_name_length(self):
        parent_bid = models.Bid(name='Parent bid', speedrun=self.run)

        # A suggestion for a parent bid with no max length should be okay
        child = models.Bid(parent=parent_bid, name='quite a long name')
        child.clean()

        # A suggestion with a too long name should fail validation
        parent_bid.option_max_length = 5
        child = models.Bid(parent=parent_bid, name='too long')
        with self.assertRaises(ValidationError):
            child.clean()

        # A suggestion with okay name should pass validation
        child = models.Bid(parent=parent_bid, name='short')
        child.clean()

    def test_bid_max_length_change(self):
        parent_bid = models.Bid.objects.create(
            name='Parent bid',
            speedrun=self.run,
            allowuseroptions=True,
            option_max_length=16,
        )

        models.Bid.objects.create(parent=parent_bid, name='within limit')
        parent_bid.option_max_length = 8

        with self.assertRaises(ValidationError):
            parent_bid.clean()

    def test_blank_bid(self):
        donation = randgen.generate_donation(self.rand, event=self.event)
        bid = models.DonationBid(amount=5, donation=donation)
        bid.clean()  # raises nothing, the rest of the validation will complain about it being blank

    def test_incorrect_target(self):
        donation = randgen.generate_donation(self.rand, event=self.event)
        bid = models.DonationBid(
            bid=self.opened_parent_bid, amount=5, donation=donation
        )

        with self.assertRaises(ValidationError):
            bid.clean()


class TestBidAdmin(TestBidBase):
    def setUp(self):
        super(TestBidAdmin, self).setUp()
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )

    def test_bid_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_bid_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_bid_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_bid_change', args=(self.opened_bid.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_donation_bid_admin(self):
        self.donation_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.opened_bid
        )
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_donationbid_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donationbid_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_donationbid_change', args=(self.donation_bid.id,))
        )
        self.assertEqual(response.status_code, 200)


class TestBidViews(TestBidBase):
    def test_bid_list(self):
        resp = self.client.get(reverse('tracker:bidindex'))
        self.assertRedirects(
            resp, reverse('tracker:bidindex', args=(self.event.short,))
        )

        resp = self.client.get(reverse('tracker:bidindex', args=(self.event.short,)))
        self.assertContains(resp, self.opened_parent_bid.name)
        self.assertContains(resp, self.opened_parent_bid.get_absolute_url())
        self.assertContains(resp, self.opened_bid.name)
        self.assertContains(resp, self.opened_bid.get_absolute_url())
        self.assertContains(resp, self.closed_parent_bid.name)
        self.assertContains(resp, self.closed_parent_bid.get_absolute_url())
        self.assertContains(resp, self.closed_bid.name)
        self.assertContains(resp, self.closed_bid.get_absolute_url())
        self.assertNotContains(resp, self.hidden_bid.name)
        self.assertNotContains(resp, self.hidden_bid.get_absolute_url())
        self.assertNotContains(resp, self.denied_bid.name)
        self.assertNotContains(resp, self.denied_bid.get_absolute_url())
        self.assertNotContains(resp, self.pending_bid.name)
        self.assertNotContains(resp, self.pending_bid.get_absolute_url())
        self.assertNotContains(resp, 'Invalid Variable')

    def test_bid_detail(self):
        resp = self.client.get(
            reverse('tracker:bid', args=(self.opened_parent_bid.id,))
        )
        self.assertContains(resp, self.opened_parent_bid.name)
        self.assertContains(resp, self.opened_bid.name)
        self.assertContains(resp, self.opened_bid.get_absolute_url())
        self.assertNotContains(resp, 'Invalid Variable')

        resp = self.client.get(
            reverse('tracker:bid', args=(self.closed_parent_bid.id,))
        )
        self.assertContains(resp, self.closed_parent_bid.name)
        self.assertContains(resp, self.closed_bid.name)
        self.assertContains(resp, self.closed_bid.get_absolute_url())
        self.assertNotContains(resp, 'Invalid Variable')

        for bid in [self.opened_bid, self.closed_bid]:
            models.DonationBid.objects.create(donation=self.donation, bid=bid, amount=1)
            resp = self.client.get(reverse('tracker:bid', args=(bid.id,)))
            self.assertContains(resp, bid.parent.name)
            self.assertContains(resp, bid.name)
            self.assertContains(resp, self.donation.get_absolute_url())
            self.assertContains(resp, self.donor.visible_name())
            self.assertContains(
                resp, self.donor.cache_for(self.event.id).get_absolute_url()
            )
            self.assertNotContains(resp, 'Invalid Variable')
        for bid in [self.hidden_bid, self.denied_bid, self.pending_bid]:
            resp = self.client.get(reverse('tracker:bid', args=(bid.id,)))
            self.assertEqual(
                resp.status_code, 404, msg=f'{bid} detail page did not 404'
            )
