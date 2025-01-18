from datetime import datetime, timedelta
from typing import Optional

from django.contrib.auth.models import Permission, User

from tracker import models
from tracker.api.serializers import DonationSerializer
from tracker.util import utcnow

from .. import randgen
from ..util import APITestCase


class TestDonations(APITestCase):
    model_name = 'donation'
    serializer_class = DonationSerializer
    extra_serializer_kwargs = dict(
        with_all_comments=True,
        with_mod_comments=True,
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
        self.event.use_one_step_screening = False
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
                    self.event.use_one_step_screening = True
                    self.event.save()
                    self.patch_noun(
                        donation, noun='flag', status_code=400, user=self.add_user
                    )

                self.event.use_one_step_screening = False
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

                # no special permission for one step screening
                self.event.use_one_step_screening = True
                self.event.save()
                data = self.patch_noun(
                    donation, noun='send-to-reader', user=self.add_user
                )
                self.assertV2ModelPresent(donation, data)
                self.assertEqual(donation.commentstate, 'APPROVED')
                self.assertEqual(donation.readstate, 'READY')

                donation.readstate = 'PENDING'
                donation.save()

                self.event.use_one_step_screening = False
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
