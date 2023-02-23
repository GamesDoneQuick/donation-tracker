import random

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from tracker import models

from . import randgen
from .util import long_ago_noon, today_noon


class TestBidBase(TestCase):
    def setUp(self):
        super().setUp()
        self.rand = random.Random(None)
        self.event = models.Event.objects.get_or_create(
            short='test',
            defaults=dict(datetime=today_noon, targetamount=5),
        )[0]
        self.locked_event = models.Event.objects.get_or_create(
            short='locked',
            locked=True,
            defaults=dict(datetime=long_ago_noon, targetamount=5),
        )[0]
        self.run = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='0:45:00',
            setup_time='0:05:00',
            order=1,
        )
        self.locked_run = models.SpeedRun.objects.create(
            event=self.locked_event,
            name='Test Locked Run',
            run_time='0:35:00',
            setup_time='0:05:00',
            order=1,
        )
        self.donor = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com'
        )
        self.donation = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=5, transactionstate='COMPLETED'
        )
        self.donation2 = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=10, transactionstate='COMPLETED'
        )
        # enough to cover the first link in the chain, but not the second
        self.donation3 = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=625, transactionstate='COMPLETED'
        )
        # covers the remainder
        self.donation4 = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=250, transactionstate='COMPLETED'
        )
        self.opened_parent_bid = models.Bid.objects.create(
            name='Opened Parent Test',
            speedrun=self.run,
            state='OPENED',
            allowuseroptions=True,
        )
        self.opened_parent_bid.save()
        self.closed_parent_bid = models.Bid.objects.create(
            name='Closed Parent Test', speedrun=self.run, state='CLOSED'
        )
        self.closed_parent_bid.save()
        self.hidden_parent_bid = models.Bid.objects.create(
            name='Hidden Parent Test', speedrun=self.run, state='HIDDEN'
        )
        self.hidden_parent_bid.save()
        self.opened_bid = models.Bid.objects.create(
            name='Opened Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='OPENED',
        )
        self.opened_bid.save()
        # this one needs a different parent because of the way opened/closed interacts through the tree
        self.closed_bid = models.Bid.objects.create(
            name='Closed Test',
            istarget=True,
            parent=self.closed_parent_bid,
            state='CLOSED',
        )
        self.closed_bid.save()
        self.hidden_bid = models.Bid.objects.create(
            name='Hidden Test',
            istarget=True,
            parent=self.hidden_parent_bid,
            state='HIDDEN',
        )
        self.hidden_bid.save()
        self.denied_bid = models.Bid.objects.create(
            name='Denied Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='DENIED',
        )
        self.denied_bid.save()
        self.pending_bid = models.Bid.objects.create(
            name='Pending Test',
            istarget=True,
            parent=self.opened_parent_bid,
            state='PENDING',
        )
        self.pending_bid.save()
        self.challenge = models.Bid.objects.create(
            name='Challenge',
            istarget=True,
            state='OPENED',
            pinned=True,
            goal=15,
            speedrun=self.run,
        )
        self.locked_challenge = models.Bid.objects.create(
            name='Challenge on Locked Event',
            istarget=True,
            state='OPENED',
            goal=15,
            event=self.locked_event,
        )
        self.locked_parent_bid = models.Bid.objects.create(
            name='Parent on Locked Event',
            state='OPENED',
            allowuseroptions=True,
            event=self.locked_event,
        )
        self.challenge_donation = models.DonationBid.objects.create(
            donation=self.donation2,
            bid=self.challenge,
            amount=self.donation2.amount,
        )
        self.chain_top = models.Bid.objects.create(
            name='Chain Top',
            istarget=True,
            state='OPENED',
            chain=True,
            pinned=True,
            goal=500,
            event=self.event,
        )
        self.chain_middle = models.Bid.objects.create(
            name='Chain Middle',
            parent=self.chain_top,
            goal=250,
        )
        self.chain_bottom = models.Bid.objects.create(
            name='Chain Bottom',
            parent=self.chain_middle,
            goal=125,
        )
        # make sure the derived fields are correct
        self.opened_parent_bid.refresh_from_db()
        self.challenge.refresh_from_db()
        self.chain_top.refresh_from_db()
        self.chain_middle.refresh_from_db()
        self.chain_bottom.refresh_from_db()


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
        self.hidden_parent_bid.refresh_from_db()
        self.assertEqual(
            self.hidden_bid.total, self.donation.amount, msg='hidden bid total is wrong'
        )
        self.assertEqual(
            self.hidden_parent_bid.total,
            self.hidden_bid.total,
            msg='parent bid total is wrong',
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

    def test_chained_bid(self):
        with self.subTest(
            'should not allow siblings in a bid chain'
        ), self.assertRaises(ValidationError):
            models.Bid(parent=self.chain_top).clean()
        with self.subTest('should require a goal on a chained bid'), self.assertRaises(
            ValidationError
        ):
            models.Bid(event=self.event, chain=True).clean()
        with self.subTest(
            'should only allow the top of the chain to be targets'
        ), self.assertRaises(ValidationError):
            self.chain_middle.istarget = True
            self.chain_middle.clean()
        with self.subTest(
            'should require the top of the chain to be a target'
        ), self.assertRaises(ValidationError):
            self.chain_top.istarget = False
            self.chain_top.clean()
        with self.subTest(
            'should require a goal on new chain children'
        ), self.assertRaises(ValidationError):
            models.Bid(parent=self.chain_bottom).clean()
        with self.subTest(
            'should allow new chain children without needing to specify the chain flag'
        ):
            models.Bid(parent=self.chain_bottom, goal=50).clean()

    def test_autoclose(self):
        with self.subTest('standard challenge'):
            self.assertEqual(self.challenge.state, 'OPENED')
            self.assertTrue(self.challenge.pinned)
            models.DonationBid.objects.create(
                donation=self.donation, bid=self.challenge, amount=self.donation.amount
            )
            self.challenge.refresh_from_db()
            self.assertEqual(self.challenge.state, 'CLOSED')
            self.assertFalse(self.challenge.pinned)
        with self.subTest('chained challenge'):
            self.assertEqual(self.chain_top.state, 'OPENED')
            self.assertTrue(self.chain_top.pinned)
            models.DonationBid.objects.create(
                donation=self.donation3,
                bid=self.chain_top,
                amount=self.donation3.amount,
            )
            self.chain_top.refresh_from_db()
            self.assertEqual(self.chain_top.state, 'OPENED')
            self.assertTrue(self.chain_top.pinned)
            models.DonationBid.objects.create(
                donation=self.donation4,
                bid=self.chain_top,
                amount=self.donation4.amount,
            )
            self.chain_top.refresh_from_db()
            self.assertEqual(self.chain_top.state, 'CLOSED')
            self.assertFalse(self.chain_top.pinned)

    def test_totals(self):
        with self.subTest('chained challenge'):
            self.chain_top.refresh_from_db()
            self.chain_middle.refresh_from_db()
            self.chain_bottom.refresh_from_db()
            self.assertEqual(self.chain_top.chain_goal, 500)
            self.assertEqual(self.chain_top.chain_remaining, 375)
            self.assertEqual(self.chain_middle.chain_goal, 750)
            self.assertEqual(self.chain_middle.chain_remaining, 125)
            self.assertEqual(self.chain_bottom.chain_goal, 875)
            self.assertEqual(self.chain_bottom.chain_remaining, 0)
            models.DonationBid.objects.create(
                donation=self.donation3,
                bid=self.chain_top,
                amount=self.donation3.amount,
            )
            self.chain_top.refresh_from_db()
            self.chain_middle.refresh_from_db()
            self.chain_bottom.refresh_from_db()
            self.assertEqual(self.chain_top.total, 625)
            self.assertEqual(self.chain_top.count, 1)
            self.assertEqual(self.chain_middle.total, 125)
            # self.assertEqual(self.chain_middle.count, 0) # TODO?
            self.assertEqual(self.chain_bottom.total, 0)
            # self.assertEqual(self.chain_top.count, 0) # TODO?
            models.DonationBid.objects.create(
                donation=self.donation4,
                bid=self.chain_top,
                amount=self.donation4.amount,
            )
            self.chain_top.refresh_from_db()
            self.chain_middle.refresh_from_db()
            self.chain_bottom.refresh_from_db()
            self.assertEqual(self.chain_top.total, 875)
            self.assertEqual(self.chain_top.count, 2)
            self.assertEqual(self.chain_middle.total, 375)
            self.assertEqual(self.chain_bottom.total, 125)
            self.chain_top.goal = 400
            self.chain_top.save()
            self.chain_middle.refresh_from_db()
            self.chain_middle.goal = 150
            self.chain_middle.save()
            self.chain_top.refresh_from_db()
            self.chain_bottom.refresh_from_db()
            self.assertEqual(self.chain_top.chain_goal, 400)
            self.assertEqual(self.chain_top.chain_remaining, 275)
            self.assertEqual(self.chain_middle.chain_goal, 550)
            self.assertEqual(self.chain_middle.chain_remaining, 125)
            self.assertEqual(self.chain_bottom.chain_goal, 675)
            self.assertEqual(self.chain_bottom.chain_remaining, 0)

    def test_state_propagation(self):
        for state in ['CLOSED', 'HIDDEN', 'OPENED']:
            with self.subTest(state=state):
                self.opened_parent_bid.state = state
                self.opened_parent_bid.save()
                self.opened_bid.refresh_from_db()
                self.assertEqual(
                    self.opened_bid.state,
                    state,
                    msg=f'Child state `{state}` did not propagate from parent during parent save',
                )
                for bid in [self.pending_bid, self.denied_bid]:
                    with self.subTest(child_state=bid.state):
                        old_state = bid.state
                        bid.refresh_from_db()
                        self.assertEqual(
                            bid.state,
                            old_state,
                            msg=f'Child state `{old_state}` should not have changed during parent save',
                        )
        for state in ['CLOSED', 'HIDDEN']:
            with self.subTest(child_state=state):
                self.opened_bid.state = state
                self.opened_bid.save()
                self.opened_bid.refresh_from_db()
                self.assertEqual(
                    self.opened_bid.state,
                    'OPENED',
                    msg=f'Child state `{state}` did not propagate from parent during child save',
                )
        for state in ['PENDING', 'DENIED']:
            with self.subTest(child_state=state):
                self.opened_bid.state = state
                self.opened_bid.save()
                self.opened_bid.refresh_from_db()
                self.assertEqual(
                    self.opened_bid.state,
                    state,
                    msg=f'Child state `{state}` should not have propagated from parent during child save',
                )

    def test_pin_propagation(self):
        self.opened_parent_bid.pinned = True
        self.opened_parent_bid.save()
        self.opened_bid.refresh_from_db()
        self.assertTrue(self.opened_bid.pinned, msg='Child pin flag did not propagate')
        self.opened_parent_bid.pinned = False
        self.opened_parent_bid.save()
        self.opened_bid.refresh_from_db()
        self.assertFalse(self.opened_bid.pinned, msg='Child pin flag did not propagate')

    def test_chain_propagation(self):
        # should have happened on creation
        self.assertTrue(self.chain_middle.chain)
        self.assertTrue(self.chain_bottom.chain)

    def test_bid_option_max_length_require(self):
        # A bid cannot set option_max_length if allowuseroptions is not set
        bid = models.Bid(name='I am a bid', option_max_length=1)
        with self.assertRaisesRegex(
            ValidationError, 'Cannot set option_max_length without allowuseroptions'
        ):
            bid.clean()

    def test_bid_suggestion_name_length(self):
        parent_bid = models.Bid(name='Parent bid', event=self.event, speedrun=self.run)

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
        donation.save()
        bid = models.DonationBid.objects.create(
            bid=self.opened_parent_bid, amount=5, donation=donation
        )

        with self.assertRaises(ValidationError):
            bid.clean()

    def test_event_mismatch(self):
        other_event = randgen.generate_event(self.rand)
        other_event.save()
        other_donation = randgen.generate_donation(self.rand, event=other_event)
        other_donation.save()
        donation_bid = models.DonationBid.objects.create(
            donation=other_donation, bid=self.opened_bid, amount=other_donation.amount
        )

        with self.assertRaises(
            ValidationError, msg='Donation/Bid event mismatch should fail validation'
        ):
            donation_bid.clean()

    def test_repeat_challenge(self):
        with self.subTest('should not raise on divisors'):
            self.challenge.repeat = 5
            self.challenge.clean()
        with self.subTest('should raise with repeat and no goal'), self.assertRaises(
            ValidationError
        ):
            self.challenge.goal = None
            self.challenge.clean()
        with self.subTest('should raise on not-a-divisor'), self.assertRaises(
            ValidationError
        ):
            self.challenge.goal = 15
            self.challenge.repeat = 10
            self.challenge.clean()
        with self.subTest('should raise on negative repeat'), self.assertRaises(
            ValidationError
        ):
            self.challenge.repeat = -5
            self.challenge.clean()
        with self.subTest('should raise on non-targets'), self.assertRaises(
            ValidationError
        ):
            self.challenge.repeat = 5
            self.challenge.istarget = False
            self.challenge.clean()
        with self.subTest('should raise on child bids'), self.assertRaises(
            ValidationError
        ):
            self.opened_bid.repeat = 5
            self.opened_bid.clean()
        with self.subTest('should raise on parent bids'), self.assertRaises(
            ValidationError
        ):
            self.opened_parent_bid.repeat = 5
            self.opened_parent_bid.clean()
        with self.subTest('should raise on chained bids'), self.assertRaises(
            ValidationError
        ):
            self.chain_top.repeat = 5
            self.chain_top.clean()


class TestBidAdmin(TestBidBase):
    def setUp(self):
        super(TestBidAdmin, self).setUp()
        self.super_user = User.objects.create_superuser('admin')
        self.unlocked_user = User.objects.create(username='staff', is_staff=True)
        self.unlocked_user.user_permissions.add(
            Permission.objects.get(name='Can add bid'),
            Permission.objects.get(name='Can change bid'),
            Permission.objects.get(name='Can delete bid'),
            Permission.objects.get(name='Can view bid'),
            Permission.objects.get(name='Can add Donation Bid'),
            Permission.objects.get(name='Can change Donation Bid'),
            Permission.objects.get(name='Can delete Donation Bid'),
            Permission.objects.get(name='Can view Donation Bid'),
        )
        self.view_user = User.objects.create(username='view', is_staff=True)
        self.view_user.user_permissions.add(
            Permission.objects.get(name='Can view bid'),
            Permission.objects.get(name='Can view Donation Bid'),
        )

    def test_bid_admin(self):
        with self.subTest('super user'):
            self.client.force_login(self.super_user)
            response = self.client.get(reverse('admin:tracker_bid_changelist'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(reverse('admin:tracker_bid_add'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.opened_bid.id,))
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['has_change_permission'])
            self.assertTrue(response.context['has_delete_permission'])
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.locked_challenge.id,))
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['has_change_permission'])
            self.assertTrue(response.context['has_delete_permission'])
        with self.subTest('staff user'):
            self.client.force_login(self.unlocked_user)
            response = self.client.get(reverse('admin:tracker_bid_changelist'))
            # need special permission to add new top level bid
            self.assertFalse(response.context['has_add_permission'])
            self.assertEqual(response.status_code, 200)
            # fresh bid with no donations
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.opened_bid.id,))
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['has_change_permission'])
            self.assertTrue(response.context['has_delete_permission'])
            # bid on locked event
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.locked_challenge.id,))
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context['has_change_permission'])
            self.assertFalse(response.context['has_delete_permission'])
            # bid has donations, normal user cannot delete
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.challenge.id,))
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['has_change_permission'])
            self.assertFalse(response.context['has_delete_permission'])
        with self.subTest('view user'):
            self.client.force_login(self.view_user)
            response = self.client.get(reverse('admin:tracker_bid_changelist'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(
                reverse('admin:tracker_bid_change', args=(self.opened_bid.id,))
            )
            self.assertEqual(response.status_code, 200)

    def test_bid_admin_set_state(self):
        with self.subTest('super user'):
            self.client.force_login(self.super_user)
            self.locked_challenge.state = 'CLOSED'
            self.locked_challenge.save()
            response = self.client.post(
                reverse('admin:tracker_bid_changelist'),
                {
                    'action': 'bid_open_action',
                    ACTION_CHECKBOX_NAME: [
                        self.closed_bid.id,
                        self.hidden_parent_bid.id,
                        self.locked_challenge.id,
                    ],
                },
            )
            self.assertEqual(response.status_code, 302)
            with self.subTest('should not change child bids without parent'):
                self.closed_bid.refresh_from_db()
                self.assertEqual(self.closed_bid.state, 'CLOSED')
            with self.subTest('should propagate change to children'):
                self.hidden_parent_bid.refresh_from_db()
                self.assertEqual(self.hidden_parent_bid.state, 'OPENED')
                self.hidden_bid.refresh_from_db()
                self.assertEqual(self.hidden_bid.state, 'OPENED')
            with self.subTest('should change locked events with permission'):
                self.locked_challenge.refresh_from_db()
                self.assertEqual(self.locked_challenge.state, 'OPENED')

        with self.subTest('staff user'):
            self.client.force_login(self.unlocked_user)
            response = self.client.post(
                reverse('admin:tracker_bid_changelist'),
                {
                    'action': 'bid_close_action',
                    ACTION_CHECKBOX_NAME: [self.locked_challenge.id],
                },
            )
            self.assertEqual(response.status_code, 302)
            with self.subTest('should not change locked events without permission'):
                self.locked_challenge.refresh_from_db()
                self.assertEqual(self.locked_challenge.state, 'OPENED')

    def test_donation_bid_admin(self):
        self.donation_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.opened_bid
        )
        self.locked_donation_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.locked_challenge
        )
        with self.subTest('super user'):
            self.client.force_login(self.super_user)
            response = self.client.get(reverse('admin:tracker_donationbid_changelist'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(reverse('admin:tracker_donationbid_add'))
            self.assertEqual(response.status_code, 403)
            response = self.client.get(
                reverse(
                    'admin:tracker_donationbid_change', args=(self.donation_bid.id,)
                )
            )
            self.assertEqual(response.status_code, 200)
            response = self.client.get(
                reverse(
                    'admin:tracker_donationbid_change',
                    args=(self.locked_donation_bid.id,),
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['has_change_permission'])

        with self.subTest('staff user'):
            self.client.force_login(self.unlocked_user)
            response = self.client.get(
                reverse(
                    'admin:tracker_donationbid_change',
                    args=(self.locked_donation_bid.id,),
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context['has_change_permission'])


class TestBidViews(TestBidBase):
    def test_bid_event_list(self):
        resp = self.client.get(
            reverse(
                'tracker:bidindex',
            )
        )
        self.assertContains(resp, self.event.name)
        self.assertContains(resp, reverse('tracker:bidindex', args=(self.event.short,)))

    def test_bid_list(self):
        models.DonationBid.objects.create(
            donation=self.donation, bid=self.opened_bid, amount=self.donation.amount
        )
        resp = self.client.get(reverse('tracker:bidindex', args=(self.event.short,)))
        self.assertContains(
            resp, f'Total: ${(self.donation.amount + self.donation2.amount):.2f}'
        )
        self.assertContains(resp, f'Choice Total: ${self.donation.amount:.2f}')
        self.assertContains(resp, f'Challenge Total: ${self.donation2.amount:.2f}')
        self.assertContains(resp, self.opened_parent_bid.name)
        self.assertContains(resp, self.opened_parent_bid.get_absolute_url())
        self.assertContains(resp, self.opened_bid.name)
        self.assertContains(resp, self.opened_bid.get_absolute_url())
        self.assertContains(resp, self.closed_parent_bid.name)
        self.assertContains(resp, self.closed_parent_bid.get_absolute_url())
        self.assertContains(resp, self.closed_bid.name)
        self.assertContains(resp, self.closed_bid.get_absolute_url())
        self.assertNotContains(resp, self.hidden_parent_bid.name)
        self.assertNotContains(resp, self.hidden_parent_bid.get_absolute_url())
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
            randgen.generate_donations(
                self.rand, self.event, 75, bid_targets_list=[bid]
            )
            resp = self.client.get(reverse('tracker:bid', args=(bid.id,)))
            self.assertContains(resp, bid.parent.name)
            self.assertContains(resp, bid.name)
            self.assertContains(resp, self.donation.get_absolute_url())
            self.assertContains(resp, self.donor.visible_name())
            self.assertContains(
                resp, self.donor.cache_for(self.event.id).get_absolute_url()
            )
            self.assertContains(resp, 'of 2')
            self.assertNotContains(resp, 'Invalid Variable')
            resp = self.client.get(
                reverse('tracker:bid', args=(bid.id,)), data={'page': 2}
            )
            self.assertContains(resp, 'of 2')
            self.assertNotContains(resp, 'Invalid Variable')
            resp = self.client.get(
                reverse('tracker:bid', args=(bid.id,)), data={'page': 3}
            )
            self.assertEqual(
                resp.status_code, 404, msg=f'{bid} detail empty page did not 404'
            )
            resp = self.client.get(
                reverse('tracker:bid', args=(bid.id,)), data={'page': 'foo'}
            )
            self.assertEqual(
                resp.status_code, 404, msg=f'{bid} detail invalid page did not 404'
            )
        for bid in [self.hidden_bid, self.denied_bid, self.pending_bid]:
            resp = self.client.get(reverse('tracker:bid', args=(bid.id,)))
            self.assertEqual(
                resp.status_code, 404, msg=f'{bid} detail page did not 404'
            )
