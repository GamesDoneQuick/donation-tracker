import random
from datetime import datetime, timedelta
from typing import Optional

from django.contrib.auth.models import Permission, User
from django.test import TransactionTestCase

from tracker import models
from tracker.api.serializers import DonationSerializer
from tracker.models import Donor
from tracker.util import utcnow

from .. import randgen
from ..randgen import generate_donation, generate_donor, generate_event
from ..util import APITestCase


class TestDonations(APITestCase):
    model_name = 'donation'
    serializer_class = DonationSerializer
    extra_serializer_kwargs = dict(
        with_all_comments=True,
        with_mod_comments=True,
        with_groups=True,
        with_permissions=(
            'tracker.view_donation',
            'tracker.view_comments',
            'tracker.view_bid',
        ),
    )
    add_user_permissions = ['view_comments', 'view_bid']

    def setUp(self):
        super().setUp()
        self.opened_parent_bid = randgen.generate_bid(
            self.rand,
            event=self.event,
            allowuseroptions=True,
            min_children=0,
            max_children=0,
        )[0]
        self.opened_parent_bid.save()
        self.pending_child = randgen.generate_bid(
            self.rand,
            parent=self.opened_parent_bid,
            allowuseroptions=False,
            state='PENDING',
        )[0]
        self.pending_child.save()
        self.event.screening_mode = 'two_pass'
        self.event.save()
        self.other_event = randgen.build_random_event(
            self.rand, num_runs=2, num_donors=2
        )

    def generate_donations(
        self,
        event: models.Event,
        *,
        count=1,
        state: str,
        transactionstate='COMPLETED',
        time: Optional[datetime] = None,
    ):
        commentstate = 'PENDING'
        readstate = 'PENDING'
        if state == 'pending':
            commentstate = 'PENDING'
            readstate = 'PENDING'
        elif state == 'flagged':
            commentstate = 'APPROVED'
            readstate = 'FLAGGED'
        elif state == 'ready':
            commentstate = 'APPROVED'
            readstate = 'READY'
        elif state == 'read':
            commentstate = 'APPROVED'
            readstate = 'READ'
        elif state == 'denied':
            commentstate = 'DENIED'
            readstate = 'IGNORED'
        elif state == 'ignored':
            commentstate = 'APPROVED'
            readstate = 'IGNORED'

        if time is None:
            time = utcnow()

        donations = randgen.generate_donations(
            self.rand,
            event,
            count,
            start_time=time,
            end_time=time + timedelta(seconds=1),
            transactionstate=transactionstate,
            commentstate=commentstate,
            readstate=readstate,
        )
        return donations

    def test_fetch(self):
        with self.saveSnapshot():
            date = utcnow()
            old_donations = {}
            new_donations = {}
            for state in ['pending', 'flagged', 'ready', 'read', 'denied', 'ignored']:
                old_donations[state] = self.generate_donations(
                    self.event,
                    count=2,
                    state=state,
                    time=date.replace(year=2),
                )
                new_donations[state] = self.generate_donations(
                    self.event,
                    count=2,
                    state=state,
                    time=date.replace(year=9998),
                )
                # other event
                self.generate_donations(self.other_event, count=1, state=state)

            with self.subTest('unprocessed'):
                data = self.get_noun(
                    'unprocessed',
                    kwargs={'event_pk': self.event.pk},
                    data={'all_bids': ''},
                    user=self.add_user,
                )
                self.assertExactV2Models(
                    old_donations['pending'] + new_donations['pending'], data
                )

                with self.subTest('time filter'):
                    data = self.get_noun(
                        'unprocessed',
                        kwargs={'event_pk': self.event.pk},
                        data={'all_bids': '', 'time_gte': date},
                    )
                    self.assertExactV2Models(new_donations['pending'], data)

            with self.subTest('flagged'):
                data = self.get_noun(
                    'flagged', kwargs={'event_pk': self.event.pk}, data={'all_bids': ''}
                )
                self.assertExactV2Models(
                    old_donations['flagged'] + new_donations['flagged'], data
                )

                with self.subTest('time filter'):
                    data = self.get_noun(
                        'flagged',
                        kwargs={'event_pk': self.event.pk},
                        data={'all_bids': '', 'time_gte': date},
                    )
                    self.assertExactV2Models(new_donations['flagged'], data)

            data = self.get_list(user=None)
            self.assertExactV2Models(
                DonationSerializer(
                    models.Donation.objects.completed().prefetch_public_bids(),
                    many=True,
                ).data,
                data,
                serializer_kwargs=dict(
                    with_all_comments=False, with_mod_comments=False
                ),
            )

    def test_patch(self):
        donation = self.generate_donations(self.event, count=1, state='approved')[0]
        user = User.objects.create()

        with self.saveSnapshot():
            with self.subTest('unprocess'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(
                        donation, noun='unprocess', status_code=403, user=None
                    )
                    self.patch_noun(
                        donation, noun='unprocess', status_code=403, user=user
                    )

                data = self.patch_noun(donation, noun='unprocess', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'PENDING')
                self.assertEqual(donation.readstate, 'PENDING')

            with self.subTest('approve comment'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(
                        donation, noun='approve-comment', status_code=403, user=None
                    )
                    self.patch_noun(
                        donation, noun='approve-comment', status_code=403, user=user
                    )

                data = self.patch_noun(
                    donation, noun='approve-comment', user=self.add_user
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'IGNORED')

            with self.subTest('deny comment'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(
                        donation, noun='deny-comment', status_code=403, user=None
                    )
                    self.patch_noun(
                        donation, noun='deny-comment', status_code=403, user=user
                    )

                data = self.patch_noun(
                    donation, noun='deny-comment', user=self.add_user
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'DENIED')
                self.assertEqual(donation.readstate, 'IGNORED')

            with self.subTest('flag comment'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(donation, noun='flag', status_code=403, user=None)
                    self.patch_noun(donation, noun='flag', status_code=403, user=user)
                    self.event.screening_mode = 'one_pass'
                    self.event.save()
                    self.patch_noun(
                        donation, noun='flag', status_code=400, user=self.add_user
                    )

                self.event.screening_mode = 'two_pass'
                self.event.save()
                data = self.patch_noun(donation, noun='flag', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'FLAGGED')

            with self.subTest('send to reader'), self.assertLogsChanges(2):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(
                        donation, noun='send-to-reader', status_code=403, user=None
                    )
                    self.patch_noun(
                        donation, noun='send-to-reader', status_code=403, user=user
                    )
                    # check permission if two-step screening is active
                    self.patch_noun(
                        donation,
                        noun='send-to-reader',
                        status_code=403,
                        user=self.add_user,
                    )

                donation.readstate = 'PENDING'
                donation.save()

                # no special permission for one pass screening
                self.event.screening_mode = 'one_pass'
                self.event.save()
                data = self.patch_noun(
                    donation, noun='send-to-reader', user=self.add_user
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'READY')

                donation.readstate = 'PENDING'
                donation.save()

                self.event.screening_mode = 'two_pass'
                self.event.save()
                self.add_user.user_permissions.add(
                    Permission.objects.get(codename='send_to_reader')
                )
                self.add_user = User.objects.get(pk=self.add_user.pk)  # refresh perms
                data = self.patch_noun(
                    donation, noun='send-to-reader', user=self.add_user
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'READY')

            with self.subTest('pin'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(donation, noun='pin', status_code=403, user=None)
                    self.patch_noun(donation, noun='pin', status_code=403, user=user)

                data = self.patch_noun(donation, noun='pin', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertTrue(donation.pinned)

            with self.subTest('unpin'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(donation, noun='unpin', status_code=403, user=None)
                    self.patch_noun(donation, noun='unpin', status_code=403, user=user)

                data = self.patch_noun(donation, noun='unpin', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertFalse(donation.pinned)

            with self.subTest('read'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(donation, noun='read', status_code=403, user=None)
                    self.patch_noun(donation, noun='read', status_code=403, user=user)

                data = self.patch_noun(donation, noun='read', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'READ')

            with self.subTest('ignore'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(donation, noun='ignore', status_code=403, user=None)
                    self.patch_noun(donation, noun='ignore', status_code=403, user=user)

                data = self.patch_noun(donation, noun='ignore', user=self.add_user)
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'IGNORED')

            with self.subTest('comment'), self.assertLogsChanges(1):
                with self.suppressSnapshot(), self.subTest('error cases'):
                    self.patch_noun(
                        donation, noun='comment', status_code=403, user=None
                    )
                    self.patch_noun(
                        donation, noun='comment', status_code=403, user=user
                    )
                    self.patch_noun(
                        donation,
                        noun='comment',
                        status_code=400,
                        user=self.add_user,
                        expected_error_codes={'comment': 'required'},
                    )

                data = self.patch_noun(
                    donation,
                    noun='comment',
                    data={'comment': 'New comment.'},
                    user=self.add_user,
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.modcomment, 'New comment.')

            with self.subTest('groups'), self.assertLogsChanges(2):
                with self.suppressSnapshot():
                    # can't add a new one without permission
                    self.patch_noun(
                        donation,
                        noun='groups',
                        kwargs={'group': 'foo'},
                        status_code=400,
                    )

                self.add_permission(self.add_user, codename='add_donationgroup')

                data = self.patch_noun(donation, noun='groups', kwargs={'group': 'foo'})
                self.assertEqual(data, ['foo'])
                self.assertEqual(donation.groups.count(), 1)
                self.assertTrue(
                    models.DonationGroup.objects.filter(name='foo').exists()
                )

                with self.suppressSnapshot(), self.assertLogsChanges(0):
                    # no-op
                    self.patch_noun(donation, noun='groups', kwargs={'group': 'foo'})

                data = self.delete_noun(
                    donation, noun='groups', kwargs={'group': 'foo'}, status_code=200
                )
                self.assertEqual(data, [])
                self.assertEqual(donation.groups.count(), 0)
                self.assertTrue(
                    models.DonationGroup.objects.filter(name='foo').exists(),
                    msg='Group was unexpectedly deleted',
                )

                with self.suppressSnapshot(), self.assertLogsChanges(0):
                    # no-op
                    self.delete_noun(
                        donation,
                        noun='groups',
                        kwargs={'group': 'foo'},
                        status_code=200,
                    )


class TestDonationSerializer(TransactionTestCase):
    rand = random.Random()

    def setUp(self):
        super(TestDonationSerializer, self).setUp()
        self.event = generate_event(self.rand)
        self.event.save()
        self.donor = generate_donor(self.rand)
        self.donor.save()
        self.donation = generate_donation(self.rand, event=self.event, donor=self.donor)
        self.donation.save()

    def test_includes_all_public_fields(self):
        expected_fields = [
            'type',
            'id',
            'donor_name',
            'event',
            'domain',
            'transactionstate',
            'readstate',
            'commentstate',
            'amount',
            'currency',
            'timereceived',
            'comment',
            'commentlanguage',
            'pinned',
            'bids',
        ]

        serialized_donation = DonationSerializer(self.donation).data
        for field in expected_fields:
            self.assertIn(field, serialized_donation)

    def test_does_not_include_modcomment_without_asking(self):
        serialized_donation = DonationSerializer(self.donation).data
        self.assertNotIn('modcomment', serialized_donation)

    def test_includes_modcomment_with_permission(self):
        serialized_donation = DonationSerializer(
            self.donation,
            with_mod_comments=True,
            with_permissions=('tracker.view_donation',),
        ).data
        self.assertIn('modcomment', serialized_donation)

        with self.assertRaises(AssertionError):
            print(DonationSerializer(self.donation, with_mod_comments=True).data)

    def test_all_comments(self):
        self.donation.comment = 'famous'
        self.donation.commentstate = 'PENDING'
        serialized_donation = DonationSerializer(self.donation).data
        self.assertNotIn('comment', serialized_donation)

        with self.assertRaises(AssertionError):
            print(DonationSerializer(self.donation, with_all_comments=True).data)

        serialized_donation = DonationSerializer(
            self.donation,
            with_all_comments=True,
            with_permissions=('tracker.view_comments',),
        ).data
        self.assertEqual(serialized_donation['comment'], self.donation.comment)

    def test_groups(self):
        self.donation.groups.create(name='foo')
        serialized_donation = DonationSerializer(self.donation).data
        self.assertNotIn('groups', serialized_donation)

        with self.assertRaises(AssertionError):
            print(DonationSerializer(self.donation, with_groups=True).data)

        serialized_donation = DonationSerializer(
            self.donation, with_groups=True, with_permissions=('tracker.view_donation',)
        ).data
        self.assertEqual(serialized_donation['groups'], ['foo'])

    def test_anonymous_donor_says_anonymous(self):
        self.donation.donor = generate_donor(self.rand, visibility='ANON')
        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], Donor.ANONYMOUS)

    def test_no_alias_says_anonymous(self):
        # Providing no alias sets requestedvisibility to ANON from the frontend.
        # This should probably be codified on the backend in the future.
        self.donation.requestedalias = ''
        self.donation.requestedvisibility = 'ANON'

        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], Donor.ANONYMOUS)

    def test_requestedalias_different_donor_says_requestedalias(self):
        # Ensure that the visible name tied to the donation matches what the
        # user entered, regardless of who we attribute it to internally.
        self.donation.requestedalias = 'requested by donation'
        self.donation.donor = generate_donor(
            self.rand, alias='requested_by_donor', visibility='ALIAS'
        )

        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], 'requested by donation')
