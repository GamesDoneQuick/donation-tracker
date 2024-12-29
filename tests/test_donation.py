# coding: utf-8

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin import AdminSite
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from tracker import admin, models

from .util import (
    AssertionHelpers,
    MigrationsTestCase,
    create_ipn,
    today_noon,
    tomorrow_noon,
)


class TestDonation(TestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            receivername='Médecins Sans Frontières',
            datetime=datetime.datetime(2018, 1, 1),
        )
        self.alias_donor = models.Donor.objects.create(
            visibility='ALIAS', alias='FooBar'
        )
        self.anon_donor = models.Donor.objects.create(visibility='ANON')

    def test_anonymous(self):
        # Anonymous donation is anonymous
        donation = models.Donation(
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from an anonymous donor with CURR is anonymous
        donation = models.Donation(
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=models.Donor(visibility='ANON'),
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from a non-anonymous donor with CURR is not anonymous
        donation = models.Donation(
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=models.Donor(visibility='ALIAS'),
            event=self.event,
        )
        self.assertFalse(donation.anonymous())

    def test_approve_if_anonymous_and_no_comment(self):
        # If the comment was already read (or anything not pending), don't act
        donation = models.Donation.objects.create(
            readstate='READ',
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READ')

        # With no threshold given, leave as is
        donation = models.Donation.objects.create(
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        self.event.auto_approve_threshold = 5
        self.event.save()

        # With a threshold and a donation above it, send to reader
        donation = models.Donation.objects.create(
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READY')

        # With a threshold and a donation below it, ignore
        donation = models.Donation.objects.create(
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'IGNORED')

        # Donation with a non-anonymous donor should not bypass screening
        donation = models.Donation.objects.create(
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='ALIAS',
            donor=self.alias_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        # Donation with a comment should not bypass screening
        donation = models.Donation.objects.create(
            amount=Decimal(10),
            comment='Hello',
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        # edge case: threshold of $0 still approves

        self.event.auto_approve_threshold = 0
        self.event.save()

        donation = models.Donation.objects.create(
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=self.anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READY')

    def test_absent_comment(self):
        self.assertEqual(
            models.Donation.objects.create(
                amount=10,
                domain='LOCAL',
                event=self.event,
                commentstate='PENDING',
                comment=' ',
                donor=self.anon_donor,
            ).commentstate,
            'ABSENT',
        )
        self.assertEqual(
            models.Donation.objects.create(
                amount=10,
                domain='LOCAL',
                event=self.event,
                commentstate='ABSENT',
                comment='Not blank.',
                donor=self.anon_donor,
            ).commentstate,
            'PENDING',
        )

    @override_settings(PAYPAL_TEST=False)
    def test_queryset(self):
        models.Donation.objects.create(
            amount=10,
            domain='PAYPAL',
            event=self.event,
            transactionstate='PENDING',
        )
        test_donation = models.Donation.objects.create(
            amount=10,
            domain='PAYPAL',
            event=self.event,
            transactionstate='COMPLETED',
            testdonation=True,
        )
        completed_donation = models.Donation.objects.create(
            amount=10,
            domain='PAYPAL',
            event=self.event,
            transactionstate='COMPLETED',
            timereceived=today_noon,
        )
        self.assertQuerySetEqual(
            models.Donation.objects.completed(),
            models.Donation.objects.filter(id=completed_donation.id),
        )

        with override_settings(PAYPAL_TEST=True):
            self.assertQuerySetEqual(
                models.Donation.objects.completed(),
                models.Donation.objects.filter(
                    id__in=[completed_donation.id, test_donation.id]
                ),
            )

        # edge case (would require manual intervention to get it into this state)

        completed_donation.comment = 'Not blank.'
        completed_donation.commentstate = 'PENDING'
        completed_donation.readstate = 'IGNORED'
        completed_donation.save()
        self.assertQuerySetEqual(
            models.Donation.objects.to_process(),
            models.Donation.objects.filter(id=completed_donation.id),
        )

        completed_donation.comment = ''  # commentstate will be ABSENT
        completed_donation.readstate = 'PENDING'
        completed_donation.save()
        self.assertQuerySetEqual(
            models.Donation.objects.to_process(),
            models.Donation.objects.filter(id=completed_donation.id),
        )

        completed_donation.readstate = 'READY'
        completed_donation.save()
        self.assertQuerySetEqual(
            models.Donation.objects.to_process(), models.Donation.objects.none()
        )
        self.assertQuerySetEqual(
            models.Donation.objects.to_read(),
            models.Donation.objects.filter(id=completed_donation.id),
        )

        self.event.use_one_step_screening = False
        self.event.save()
        completed_donation.refresh_from_db()
        completed_donation.commentstate = 'APPROVED'
        completed_donation.readstate = 'FLAGGED'
        completed_donation.save()
        self.assertQuerySetEqual(
            models.Donation.objects.to_process(), models.Donation.objects.none()
        )
        self.assertQuerySetEqual(
            models.Donation.objects.to_approve(),
            models.Donation.objects.filter(id=completed_donation.id),
        )

        completed_donation.readstate = 'READ'
        completed_donation.save()
        self.assertQuerySetEqual(
            models.Donation.objects.to_read(), models.Donation.objects.none()
        )

        self.assertQuerySetEqual(
            models.Donation.objects.recent(
                5, today_noon + datetime.timedelta(minutes=5)
            ),
            models.Donation.objects.filter(id=completed_donation.id),
        )
        self.assertQuerySetEqual(
            models.Donation.objects.recent(
                5, today_noon + datetime.timedelta(minutes=10)
            ),
            models.Donation.objects.none(),
        )

    @patch('tracker.tasks.post_donation_to_postbacks')
    def test_local_donation_broadcast(self, task):
        with override_settings(TRACKER_HAS_CELERY=True):
            donation = models.Donation.objects.create(amount=50)
            task.delay.assert_called_with(donation.id)
            task.assert_not_called()
            task.reset_mock()

            donation.save()
            task.delay.assert_not_called()

        with override_settings(TRACKER_HAS_CELERY=False):
            donation = models.Donation.objects.create(amount=50)
            task.assert_called_with(donation.id)
            task.delay.assert_not_called()
            task.reset_mock()

            donation.save()
            task.assert_not_called()


class TestDonationAdmin(TestCase, AssertionHelpers):
    def setUp(self):
        self.donation_admin = admin.donation.DonationAdmin(models.Donation, AdminSite())
        self.factory = RequestFactory()
        self.super_user = User.objects.create_superuser('admin')
        self.unlocked_user = User.objects.create(username='staff', is_staff=True)
        self.unlocked_user.user_permissions.add(
            Permission.objects.get(name='Can add donation'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can delete donation'),
            Permission.objects.get(name='Can view donation'),
        )
        self.view_user = User.objects.create(username='view', is_staff=True)
        self.view_user.user_permissions.add(
            Permission.objects.get(name='Can view donation'),
        )
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', datetime=today_noon
        )

        self.donor = models.Donor.objects.create(firstname='John', lastname='Doe')
        self.donation = models.Donation.objects.create(
            donor=self.donor,
            amount=5,
            event=self.event,
            transactionstate='COMPLETED',
            domain='LOCAL',
        )

    def test_donation_admin(self):
        with self.subTest('super user'):
            self.client.force_login(self.super_user)
            response = self.client.get(reverse('admin:tracker_donation_changelist'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(reverse('admin:tracker_donation_add'))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(
                reverse('admin:tracker_donation_change', args=(self.donation.id,))
            )
            self.assertEqual(response.status_code, 200)
        with self.subTest('staff user'):
            self.client.force_login(self.unlocked_user)
            self.event.locked = True
            self.event.save()
            with self.subTest(
                'should not be able to edit a donation on a locked event'
            ):
                response = self.client.get(
                    reverse('admin:tracker_donation_change', args=(self.donation.id,))
                )
                self.assertFalse(response.context['has_change_permission'])
                self.assertFalse(response.context['has_delete_permission'])
                response = self.client.post(
                    reverse('admin:tracker_donation_change', args=(self.donation.id,))
                )
                self.assertEqual(response.status_code, 403)
            with self.subTest('should not be able to add a donation to a locked event'):
                response = self.client.post(
                    reverse('admin:tracker_donation_add'),
                    data=(
                        {
                            'event': self.event.id,
                        }
                    ),
                )
                # FIXME? why did this change
                self.assertEqual(response.status_code, 403)
                # self.assertFormError(
                #     response.context['adminform'],
                #     'event',
                #     _(
                #         'Select a valid choice. That choice is not one of the available choices.'
                #     ),
                # )

    def test_donation_admin_form(self):
        # testing both get_form and get_readonly_fields, as they will not be in
        #  base_fields if they are readonly

        # url doesn't actually matter for this test, but might as well be something relatively sensible
        request = self.factory.get(reverse('admin:tracker_donation_add'))

        with self.subTest('super user'):
            request.user = self.super_user

            form = self.donation_admin.get_form(request)
            self.assertSetDisjoint(
                form.base_fields,
                {'transactionstate', 'readstate', 'commentstate'},
                msg='Fields are read only on creation',
            )

            form = self.donation_admin.get_form(request, self.donation)
            self.assertNotIn(
                'commentstate', form.base_fields, msg='Read only when comment is blank'
            )

            self.donation.comment = 'Not blank.'
            self.donation.save()
            form = self.donation_admin.get_form(request, self.donation)
            self.assertIn(
                'commentstate',
                form.base_fields,
                msg='Writeable when comment is present',
            )
            self.assertNotIn(
                'ABSENT',
                (c[0] for c in form.base_fields['commentstate'].choices),
                msg='Absent state not selectable when comment is present',
            )

            self.assertNotIn(
                'FLAGGED',
                (c[0] for c in form.base_fields['readstate'].choices),
                msg='Flagged state not selectable for one step events',
            )

            fieldsets = flatten_fieldsets(self.donation_admin.get_fieldsets(request))
            self.assertNotIn(
                'ipns_', fieldsets, msg='IPNs field should be excluded on add form'
            )

            fieldsets = flatten_fieldsets(
                self.donation_admin.get_fieldsets(request, self.donation)
            )
            self.assertNotIn(
                'ipns_',
                fieldsets,
                msg='IPNs field should be excluded on local donations',
            )

            self.donation.domain = 'PAYPAL'
            self.donation.save()

            fieldsets = flatten_fieldsets(
                self.donation_admin.get_fieldsets(request, self.donation)
            )
            self.assertIn('ipns_', fieldsets, msg='IPNs field is missing')

        with self.subTest('normal editor'):
            request.user = self.unlocked_user
            form = self.donation_admin.get_form(request)
            self.assertSetDisjoint(
                form.base_fields,
                {'domain', 'fee', 'testdonation'},
                msg='Fields are read only without special permission',
            )

            form = self.donation_admin.get_form(request, self.donation)
            self.assertNotIn(
                'transactionstate',
                form.base_fields,
                msg='Field is read only without special permission',
            )

            self.donation.domain = 'PAYPAL'
            self.donation.save()
            form = self.donation_admin.get_form(request, self.donation)
            self.assertSetDisjoint(
                form.base_fields,
                {'donor', 'event', 'timereceived', 'amount', 'currency'},
                msg='Fields are read only for non-local donations without special permission',
            )
            self.assertIn(
                'readstate', form.base_fields, msg='Field is editable when not READY'
            )

            self.event.use_one_step_screening = False
            self.event.save()
            self.donation.refresh_from_db()
            self.donation.readstate = 'READY'
            self.donation.save()
            form = self.donation_admin.get_form(request, self.donation)
            self.assertIn(
                'READY',
                (c[0] for c in form.base_fields['readstate'].choices),
                msg='Field is already READY, so it is a valid choice for first-pass screeners (and hosts)',
            )

            self.donation.readstate = 'FLAGGED'
            self.donation.save()
            form = self.donation_admin.get_form(request, self.donation)
            self.assertNotIn(
                'READY',
                (c[0] for c in form.base_fields['readstate'].choices),
                msg='Cannot set to READY without permission',
            )

            request.user.user_permissions.add(
                Permission.objects.get(codename='send_to_reader')
            )
            # cleanest way to reset permissions cache, refresh_from_db is not enough
            request.user = User.objects.get(id=request.user.id)
            form = self.donation_admin.get_form(request, self.donation)
            self.assertIn(
                'READY',
                (c[0] for c in form.base_fields['readstate'].choices),
                msg='Can set to READY with permission',
            )

            fieldsets = flatten_fieldsets(
                self.donation_admin.get_fieldsets(request, self.donation)
            )
            self.assertNotIn(
                'ipns_',
                fieldsets,
                msg='IPNs field should be excluded without permission',
            )

    def test_action_permissions(self):
        # url doesn't actually matter for this test, but might as well be something relatively sensible
        request = self.factory.get(reverse('admin:tracker_donation_add'))

        with self.subTest('super user'):
            request.user = self.super_user

            actions = self.donation_admin.get_actions(request)
            self.assertIn('rescan_ipns', actions, msg='IPNs action was missing.')

        with self.subTest('normal editor'):
            request.user = self.unlocked_user

            actions = self.donation_admin.get_actions(request)
            self.assertNotIn(
                'rescan_ipns',
                actions,
                msg='IPNs action should be excluded without permission.',
            )

        with self.subTest('view user'):
            request.user = self.view_user

            actions = self.donation_admin.get_actions(request)
            self.assertEqual(len(actions), 0, msg='Actions list was not empty.')

    @patch('tracker.tasks.post_donation_to_postbacks')
    def test_donation_postback(self, task):
        self.client.force_login(self.super_user)

        with override_settings(TRACKER_HAS_CELERY=True):
            response = self.client.post(
                reverse('admin:tracker_donation_changelist'),
                {
                    'action': 'send_donation_postbacks',
                    ACTION_CHECKBOX_NAME: [self.donation.id],
                },
            )
            self.assertRedirects(response, reverse('admin:tracker_donation_changelist'))
            task.delay.assert_called_with(self.donation.id)
            task.assert_not_called()

        task.delay.reset_mock()
        task.reset_mock()

        with override_settings(TRACKER_HAS_CELERY=False):
            response = self.client.post(
                reverse('admin:tracker_donation_changelist'),
                {
                    'action': 'send_donation_postbacks',
                    ACTION_CHECKBOX_NAME: [self.donation.id],
                },
            )
            self.assertRedirects(response, reverse('admin:tracker_donation_changelist'))
            task.assert_called_with(self.donation.id)
            task.delay.assert_not_called()

    def test_donation_rescan_ipns(self):
        self.donation.domain = 'PAYPAL'
        self.donation.save()
        ipn = create_ipn(self.donation, 'doe@example.com')
        self.donation.ipns.clear()
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_donation_changelist'),
            {
                'action': 'rescan_ipns',
                ACTION_CHECKBOX_NAME: [self.donation.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_donation_changelist'))
        self.assertIn(ipn, self.donation.ipns.all())
        self.assertIn(self.donation, ipn.donation.all())


class TestDonationViews(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', datetime=today_noon
        )
        self.other_event = models.Event.objects.create(
            short='ev2', name='Event 2', datetime=tomorrow_noon
        )
        self.regular_donor = models.Donor.objects.create(
            alias='JohnDoe', visibility='ALIAS'
        )
        self.anonymous_donor = models.Donor.objects.create(visibility='ANON')
        self.regular_donation = models.Donation.objects.create(
            event=self.event,
            amount=5,
            donor=self.regular_donor,
            requestedalias=self.regular_donor.alias,
            transactionstate='COMPLETED',
        )
        self.anonymous_donation = models.Donation.objects.create(
            event=self.event,
            amount=15,
            donor=self.anonymous_donor,
            transactionstate='COMPLETED',
        )
        self.other_donation = models.Donation.objects.create(
            event=self.other_event,
            amount=25,
            donor=self.regular_donor,
            transactionstate='COMPLETED',
        )
        self.pending_donation = models.Donation.objects.create(
            event=self.event, amount=25, domain='PAYPAL', transactionstate='PENDING'
        )

    def test_donation_list_no_event(self):
        resp = self.client.get(reverse('tracker:donationindex'))
        self.assertContains(
            resp,
            '<small>Total (Count): $45.00 (3) &mdash; Max/Avg/Median Donation: $25.00/$15.00/$15.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donation.visible_donor_name)
        # self.assertContains(resp, self.regular_donor.get_absolute_url())
        self.assertContains(resp, self.anonymous_donation.visible_donor_name)
        # self.assertNotContains(resp, self.anonymous_donor.get_absolute_url())
        self.assertNotContains(resp, 'Invalid Variable')

    def test_donation_list_with_event(self):
        resp = self.client.get(reverse('tracker:donationindex', args=(self.event.id,)))
        self.assertContains(
            resp,
            '<small>Total (Count): $20.00 (2) &mdash; Max/Avg/Median Donation: $15.00/$10.00/$10.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donation.visible_donor_name)
        # self.assertContains(
        #     resp,
        #     self.regular_donor.cache_for(self.event.id).get_absolute_url(),
        # )
        self.assertContains(resp, self.anonymous_donation.visible_donor_name)
        # self.assertNotContains(
        #     resp, self.anonymous_donor.cache_for(self.event.id).get_absolute_url()
        # )
        self.assertNotContains(resp, 'Invalid Variable')

    def test_donation_detail(self):
        with self.subTest('pending'):
            resp = self.client.get(
                reverse('tracker:donation', args=(self.pending_donation.id,))
            )
            self.assertEqual(resp.status_code, 404)

        self.test_donation = models.Donation.objects.create(
            event=self.event,
            amount=25,
            donor=self.regular_donor,
            transactionstate='COMPLETED',
            testdonation=True,
        )

        with self.subTest('test donation'):
            resp = self.client.get(
                reverse('tracker:donation', args=(self.test_donation.id,))
            )
            self.assertEqual(resp.status_code, 200)

            with override_settings(PAYPAL_TEST=False):
                resp = self.client.get(
                    reverse('tracker:donation', args=(self.test_donation.id,))
                )
                self.assertEqual(resp.status_code, 404)


class TestDonationIPNMigration(MigrationsTestCase):
    migrate_from = (('tracker', '0055_add_donation_ipns'),)
    migrate_to = (('tracker', '0056_backfill_donation_ipns'),)

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Donation = apps.get_model('tracker', 'Donation')
        IPN = apps.get_model('ipn', 'PayPalIPN')

        event = Event.objects.create(name='Event', short='event', datetime=today_noon)

        Donation.objects.create(event=event, domain='LOCAL', domainId='123456')

        d = Donation.objects.create(event=event, domain='PAYPAL', domainId='deadbeef')
        IPN.objects.create(
            txn_id='deadbeef',
            custom=f'{d.id}:123456',
            payment_date=today_noon,
            payment_status='Pending',
        )
        IPN.objects.create(
            txn_id='deadbeef',
            custom=f'{d.id}:123456',
            created_at=tomorrow_noon,
            payment_status='Completed',
        )  # repeated

        d = Donation.objects.create(event=event, domain='PAYPAL', domainId='deafbeef')
        IPN.objects.create(
            txn_id='deafbeef',
            custom=f'{d.id}:123456',
            payment_date=today_noon,
            payment_status='Cancelled',
        )

        d = Donation.objects.create(event=event, domain='PAYPAL', domainId='deadfeed')
        IPN.objects.create(
            txn_id='deadfeed',
            custom=f'{d.id}:123456',
            payment_date=today_noon,
            payment_status='Completed',
        )
        IPN.objects.create(
            txn_id='deadfeedcb',
            custom=f'{d.id}:123456',
            payment_date=tomorrow_noon,
            payment_status='Reversed',
        )  # reversals have different txn_id

    def test_backfill(self):
        Donation = self.apps.get_model('tracker', 'Donation')
        IPN = self.apps.get_model('ipn', 'PayPalIPN')

        local = Donation.objects.get(domainId='123456')
        self.assertIsNotNone(local.timereceived)
        self.assertEqual(local.timereceived, local.cleared_at)

        ipn = IPN.objects.get(txn_id='deadbeef', payment_status='Completed')
        donation = Donation.objects.get(domainId='deadbeef')
        self.assertEqual(donation.cleared_at, ipn.created_at)
        self.assertIn(donation, ipn.donation.all())
        self.assertIn(ipn, donation.ipns.all())

        other_ipn = IPN.objects.get(txn_id='deafbeef')
        other_donation = Donation.objects.get(domainId='deafbeef')
        self.assertEqual(other_donation.cleared_at, None)
        self.assertIn(other_donation, other_ipn.donation.all())
        self.assertIn(other_ipn, other_donation.ipns.all())

        reversed_ipn = IPN.objects.get(txn_id='deadfeedcb')
        reversed_donation = Donation.objects.get(domainId='deadfeed')
        self.assertEqual(reversed_donation.cleared_at, None)
        self.assertIn(reversed_donation, reversed_ipn.donation.all())
        self.assertIn(reversed_ipn, reversed_donation.ipns.all())
