import random
from datetime import datetime, timedelta
from typing import Optional

from django.contrib.admin.models import CHANGE
from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient

from tracker.api.serializers import DonationSerializer
from tracker.api.views.donations import DONATION_CHANGE_LOG_MESSAGES
from tracker.models import Event
from tracker.util import utcnow

from .. import randgen
from ..util import APITestCase


class TestDonations(APITestCase):
    rand = random.Random()

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.super_user)
        self.event = randgen.build_random_event(self.rand, num_runs=2, num_donors=2)
        self.event.use_one_step_screening = False
        self.event.save()
        self.other_event = randgen.build_random_event(
            self.rand, num_runs=2, num_donors=2
        )

    def generate_donations(
        self,
        event: Event,
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

    ###
    # /unprocessed
    ###

    def test_unprocessed_returns_serialized_donations(self):
        donations = self.generate_donations(self.event, count=1, state='pending')
        donations.sort(key=lambda d: d.timereceived)

        self.generate_donations(self.other_event, count=1, state='pending')

        serialized = DonationSerializer(
            donations, with_permissions=('tracker.change_donation',), many=True
        )

        response = self.client.get(
            '/tracker/api/v2/donations/unprocessed/', {'event_id': self.event.pk}
        )
        self.assertEqual(response.data, serialized.data)

    def test_unprocessed_returns_oldest_unprocessed_donations_first(self):
        donations = self.generate_donations(self.event, state='pending')
        donations.sort(key=lambda d: d.timereceived)

        response = self.client.get(
            '/tracker/api/v2/donations/unprocessed/', {'event_id': self.event.pk}
        )

        self.assertEqual(len(response.data), len(donations))
        for index, donation in enumerate(donations):
            self.assertEqual(response.data[index]['id'], donation.pk)

    def test_unprocessed_returns_only_after_timestamp(self):
        date = datetime.utcnow()
        old_donations = self.generate_donations(
            self.event,
            count=2,
            state='pending',
            time=date.replace(year=2),
        )
        new_donations = self.generate_donations(
            self.event,
            count=2,
            state='pending',
            time=date.replace(year=9998),
        )

        response = self.client.get(
            '/tracker/api/v2/donations/unprocessed/',
            {
                'event_id': self.event.pk,
                'after': utcnow(),
            },
        )
        returned_ids = list(map(lambda d: d['id'], response.data))

        self.assertEqual(len(returned_ids), len(new_donations))
        for donation in new_donations:
            self.assertIn(donation.pk, returned_ids)

        for donation in old_donations:
            self.assertNotIn(donation.pk, returned_ids)

    def test_unprocessed_does_not_return_processed_donations(self):
        processed_states = ['flagged', 'ready', 'read', 'denied', 'ignored']
        for state in processed_states:
            self.generate_donations(self.event, count=1, state=state)

        response = self.client.get(
            '/tracker/api/v2/donations/unprocessed/',
            {'event_id': self.event.pk},
        )

        self.assertEqual(len(response.data), 0)

    ###
    # /flagged
    ###

    # TODO: asking for flagged donations on a one-step screening event is kind of nonsensical, but probably not
    #  worth writing a test case for

    def test_flagged_returns_serialized_donations(self):
        donations = self.generate_donations(self.event, count=1, state='flagged')
        donations.sort(key=lambda d: d.timereceived)

        self.generate_donations(self.other_event, count=1, state='flagged')

        serialized = DonationSerializer(
            donations, with_permissions=('tracker.change_donation',), many=True
        )

        response = self.client.get(
            '/tracker/api/v2/donations/flagged/', {'event_id': self.event.pk}
        )
        self.assertEqual(response.data, serialized.data)

    def test_flagged_returns_oldest_unprocessed_donations_first(self):
        donations = self.generate_donations(self.event, state='flagged')
        donations.sort(key=lambda d: d.timereceived)

        response = self.client.get(
            '/tracker/api/v2/donations/flagged/', {'event_id': self.event.pk}
        )

        self.assertEqual(len(response.data), len(donations))
        for index, donation in enumerate(donations):
            self.assertEqual(response.data[index]['id'], donation.pk)

    def test_flagged_returns_only_after_timestamp(self):
        date = utcnow()
        old_donations = self.generate_donations(
            self.event,
            count=2,
            state='flagged',
            time=date.replace(year=2),
        )
        new_donations = self.generate_donations(
            self.event,
            count=2,
            state='flagged',
            time=date.replace(year=9999),
        )

        response = self.client.get(
            '/tracker/api/v2/donations/flagged/',
            {
                'event_id': self.event.pk,
                'after': utcnow(),
            },
        )
        returned_ids = list(map(lambda d: d['id'], response.data))

        self.assertEqual(len(returned_ids), len(new_donations))
        for donation in new_donations:
            self.assertIn(donation.pk, returned_ids)

        for donation in old_donations:
            self.assertNotIn(donation.pk, returned_ids)

    def test_flagged_does_not_return_processed_donations(self):
        processed_states = ['pending', 'ready', 'read', 'denied', 'ignored']
        for state in processed_states:
            self.generate_donations(self.event, count=1, state=state)

        response = self.client.get(
            '/tracker/api/v2/donations/flagged/',
            {'event_id': self.event.pk},
        )

        self.assertEqual(len(response.data), 0)

    ###
    # /unprocess
    ###

    def test_unprocess_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/unprocess/')
        self.assertEqual(response.status_code, 403)

    def test_unprocess_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/unprocess/')
        self.assertEqual(response.status_code, 403)

    def test_unprocess_resets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='approved')[0]

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/unprocess/'
        )

        returned = response.data
        self.assertEqual(returned['commentstate'], 'PENDING')
        self.assertEqual(returned['readstate'], 'PENDING')
        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'PENDING')
        self.assertEqual(donation.readstate, 'PENDING')

    def test_unprocess_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='approved')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/unprocess/')

        self.assertLogEntry(
            'donation', donation.pk, CHANGE, DONATION_CHANGE_LOG_MESSAGES['unprocessed']
        )

    ###
    # /approve_comment
    ###

    def test_approve_comment_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/approve_comment/')
        self.assertEqual(response.status_code, 403)

    def test_approve_comment_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/approve_comment/')
        self.assertEqual(response.status_code, 403)

    def test_approve_comment_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/approve_comment/'
        )

        returned = response.data
        self.assertEqual(returned['commentstate'], 'APPROVED')
        self.assertEqual(returned['readstate'], 'IGNORED')
        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'APPROVED')
        self.assertEqual(donation.readstate, 'IGNORED')

    def test_approve_comment_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='approved')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/approve_comment/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['approved'],
        )

    ###
    # /deny_comment
    ###

    def test_deny_comment_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/deny_comment/')
        self.assertEqual(response.status_code, 403)

    def test_deny_comment_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/deny_comment/')
        self.assertEqual(response.status_code, 403)

    def test_deny_comment_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/deny_comment/'
        )

        returned = response.data
        self.assertEqual(returned['commentstate'], 'DENIED')
        self.assertEqual(returned['readstate'], 'IGNORED')
        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'DENIED')
        self.assertEqual(donation.readstate, 'IGNORED')

    def test_deny_comment_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='denied')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/deny_comment/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['denied'],
        )

    ###
    # /flag
    ###

    def test_flag_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/flag/')
        self.assertEqual(response.status_code, 403)

    def test_flag_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/flag/')
        self.assertEqual(response.status_code, 403)

    def test_flag_fails_with_one_step_screening(self):
        self.event.use_one_step_screening = True
        self.event.save()

        donation = self.generate_donations(self.event, count=1, state='')[0]

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/flag/')
        self.assertEqual(response.status_code, 400)

    def test_flag_sets_donation_state(self):

        donation = self.generate_donations(self.event, count=1, state='')[0]

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/flag/')

        returned = response.data
        self.assertEqual(returned['commentstate'], 'APPROVED')
        self.assertEqual(returned['readstate'], 'FLAGGED')
        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'APPROVED')
        self.assertEqual(donation.readstate, 'FLAGGED')

    def test_flag_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/flag/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['flagged'],
        )

    ###
    # /send_to_reader
    ###

    def test_send_to_reader_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/send_to_reader/')
        self.assertEqual(response.status_code, 403)

    def test_send_to_reader_requires_permissions(self):
        user = User.objects.create()
        user.user_permissions.add(
            Permission.objects.get(codename='change_donation'),
            Permission.objects.get(codename='send_to_reader'),
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch('/tracker/api/v2/donations/1234/send_to_reader/')
        self.assertEqual(response.status_code, 404)

    def test_send_to_reader_fails_with_only_send_to_reader_permission(self):
        user = User.objects.create()
        user.user_permissions.add(Permission.objects.get(codename='send_to_reader'))
        self.client.force_authenticate(user=user)

        response = self.client.patch('/tracker/api/v2/donations/1234/send_to_reader/')
        self.assertEqual(response.status_code, 403)

    def test_send_to_reader_checks_for_one_step_screening(self):
        user = User.objects.create()
        user.user_permissions.add(Permission.objects.get(codename='change_donation'))
        self.client.force_authenticate(user=user)

        self.event.use_one_step_screening = False
        self.event.save()
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/send_to_reader/'
        )
        self.assertEqual(response.status_code, 403)

        self.event.use_one_step_screening = True
        self.event.save()

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/send_to_reader/'
        )
        self.assertEqual(response.status_code, 200)

        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'APPROVED')
        self.assertEqual(donation.readstate, 'READY')

    def test_send_to_reader_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/send_to_reader/'
        )

        returned = response.data
        self.assertEqual(returned['commentstate'], 'APPROVED')
        self.assertEqual(returned['readstate'], 'READY')
        donation.refresh_from_db()
        self.assertEqual(donation.commentstate, 'APPROVED')
        self.assertEqual(donation.readstate, 'READY')

    def test_send_to_reader_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/send_to_reader/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['sent_to_reader'],
        )

    ###
    # /pin
    ###

    def test_pin_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/pin/')
        self.assertEqual(response.status_code, 403)

    def test_pin_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/pin/')
        self.assertEqual(response.status_code, 403)

    def test_pin_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/pin/')

        returned = response.data
        self.assertEqual(returned['pinned'], True)
        donation.refresh_from_db()
        self.assertEqual(donation.pinned, True)

    def test_pin_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/pin/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['pinned'],
        )

    ###
    # /unpin
    ###

    def test_unpin_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/unpin/')
        self.assertEqual(response.status_code, 403)

    def test_unpin_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/unpin/')
        self.assertEqual(response.status_code, 403)

    def test_unpin_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]
        donation.pinned = True
        donation.save()

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/unpin/')

        returned = response.data
        self.assertEqual(returned['pinned'], False)
        donation.refresh_from_db()
        self.assertEqual(donation.pinned, False)

    def test_unpin_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/unpin/')

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['unpinned'],
        )

    ###
    # /read
    ###

    def test_read_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/read/')
        self.assertEqual(response.status_code, 403)

    def test_read_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/read/')
        self.assertEqual(response.status_code, 403)

    def test_read_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]
        donation.pinned = True
        donation.save()

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/read/')

        returned = response.data
        self.assertEqual(returned['readstate'], 'READ')
        donation.refresh_from_db()
        self.assertEqual(donation.readstate, 'READ')

    def test_read_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/read/')

        self.assertLogEntry(
            'donation', donation.pk, CHANGE, DONATION_CHANGE_LOG_MESSAGES['read']
        )

    ###
    # /ignore
    ###

    def test_ignore_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/ignore/')
        self.assertEqual(response.status_code, 403)

    def test_ignore_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/ignore/')
        self.assertEqual(response.status_code, 403)

    def test_ignore_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]
        donation.pinned = True
        donation.save()

        response = self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/ignore/')

        returned = response.data
        self.assertEqual(returned['readstate'], 'IGNORED')
        donation.refresh_from_db()
        self.assertEqual(donation.readstate, 'IGNORED')

    def test_ignore_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(f'/tracker/api/v2/donations/{donation.pk}/ignore/')

        self.assertLogEntry(
            'donation', donation.pk, CHANGE, DONATION_CHANGE_LOG_MESSAGES['ignored']
        )

    ###
    # /comment
    ###

    def test_comment_fails_without_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/tracker/api/v2/donations/1234/comment/')
        self.assertEqual(response.status_code, 403)

    def test_comment_fails_without_change_donation_permission(self):
        user = User.objects.create()
        self.client.force_authenticate(user=user)

        response = self.client.post('/tracker/api/v2/donations/1234/comment/')
        self.assertEqual(response.status_code, 403)

    def test_comment_sets_donation_state(self):
        donation = self.generate_donations(self.event, count=1, state='ready')[0]
        donation.pinned = True
        donation.save()

        new_mod_comment = 'a new mod comment'
        response = self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/comment/',
            {'comment': new_mod_comment},
        )

        returned = response.data
        self.assertEqual(returned['modcomment'], new_mod_comment)
        donation.refresh_from_db()
        self.assertEqual(donation.modcomment, new_mod_comment)

    def test_comment_logs_changes(self):
        donation = self.generate_donations(self.event, count=1, state='pending')[0]

        self.client.patch(
            f'/tracker/api/v2/donations/{donation.pk}/comment/',
            {'comment': 'a new mod comment'},
        )

        self.assertLogEntry(
            'donation',
            donation.pk,
            CHANGE,
            DONATION_CHANGE_LOG_MESSAGES['mod_comment_edited'],
        )
