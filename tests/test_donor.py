import logging
import random
from decimal import Decimal
from unittest import skip

from django.contrib.admin import AdminSite
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from tracker import admin, models, viewutil

from . import randgen
from .util import (
    AssertionHelpers,
    MigrationsTestCase,
    long_ago_noon,
    today_noon,
    tomorrow_noon,
)


class TestDonorTotals(TestCase, AssertionHelpers):
    def setUp(self):
        self.john = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com'
        )
        self.jane = models.Donor.objects.create(
            firstname='Jane', lastname='Doe', email='janedoe@example.com'
        )
        self.ev1 = models.Event.objects.create(
            short='ev1', name='Event 1', datetime=today_noon, paypalcurrency='USD'
        )
        self.ev2 = models.Event.objects.create(
            short='ev2', name='Event 2', datetime=today_noon, paypalcurrency='USD'
        )
        self.ev3 = models.Event.objects.create(
            short='ev3', name='Event 3', datetime=today_noon, paypalcurrency='EUR'
        )

    def test_donor_cache(self):
        self.assertEqual(0, models.DonorCache.objects.count())
        d1 = models.Donation.objects.create(
            donor=self.john,
            event=self.ev1,
            amount=5,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # base case:
        #  one for donor-event
        #  one for donor-currency
        #  one for event
        #  one for currency
        self.assertEqual(4, models.DonorCache.objects.count())
        d2 = models.Donation.objects.create(
            donor=self.john,
            event=self.ev2,
            amount=5,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # additional:
        #   one for donor-event
        #   one for event
        self.assertEqual(6, models.DonorCache.objects.count())
        d3 = models.Donation.objects.create(
            donor=self.john,
            event=self.ev2,
            amount=10,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # no additional entries
        self.assertEqual(6, models.DonorCache.objects.count())
        d4 = models.Donation.objects.create(
            donor=self.jane,
            event=self.ev1,
            amount=20,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # additional:
        #   one for donor-event
        #   one for donor-currency
        self.assertEqual(8, models.DonorCache.objects.count())
        d5 = models.Donation.objects.create(
            donor=self.jane,
            event=self.ev2,
            amount=25,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # additional:
        #   one for donor-event
        self.assertEqual(9, models.DonorCache.objects.count())
        d6 = models.Donation.objects.create(
            donor=self.jane,
            event=self.ev3,
            amount=50,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        # additional:
        #   one for donor-event
        #   one for donor-currency
        #   one for event
        #   one for currency
        self.assertEqual(13, models.DonorCache.objects.count())
        self.assertDictContainsSubset(
            {
                'donation_total': 5,
                'donation_count': 1,
                'donation_max': 5,
                'donation_avg': 5,
                'donation_med': 5,
            },
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 15,
                'donation_count': 2,
                'donation_max': 10,
                'donation_avg': 7.5,
                'donation_med': 7.5,
            },
            models.DonorCache.objects.get(donor=self.john, event=self.ev2).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 20,
                'donation_count': 3,
                'donation_max': 10,
                'donation_avg': Decimal(20 / 3.0).quantize(Decimal('0.00')),
                'donation_med': 5,
            },
            models.DonorCache.objects.get(donor=self.john, currency='USD').__dict__,
        )
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, event=self.ev3).exists()
        )
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, currency='EUR').exists()
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 20,
                'donation_count': 1,
                'donation_max': 20,
                'donation_avg': 20,
                'donation_med': 20,
            },
            models.DonorCache.objects.get(donor=self.jane, event=self.ev1).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 25,
                'donation_count': 1,
                'donation_max': 25,
                'donation_avg': 25,
                'donation_med': 25,
            },
            models.DonorCache.objects.get(donor=self.jane, event=self.ev2).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 45,
                'donation_count': 2,
                'donation_max': 25,
                'donation_avg': 22.5,
                'donation_med': 22.5,
            },
            models.DonorCache.objects.get(donor=self.jane, currency='USD').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 50,
                'donation_count': 1,
                'donation_max': 50,
                'donation_avg': 50,
                'donation_med': 50,
            },
            models.DonorCache.objects.get(donor=self.jane, event=self.ev3).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 50,
                'donation_count': 1,
                'donation_max': 50,
                'donation_avg': 50,
                'donation_med': 50,
            },
            models.DonorCache.objects.get(donor=self.jane, currency='EUR').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 25,
                'donation_count': 2,
                'donation_max': 20,
                'donation_avg': 12.5,
                'donation_med': 12.5,
            },
            models.DonorCache.objects.get(donor=None, event=self.ev1).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 40,
                'donation_count': 3,
                'donation_max': 25,
                'donation_avg': Decimal(40.0 / 3).quantize(Decimal('0.00')),
                'donation_med': 10,
            },
            models.DonorCache.objects.get(donor=None, event=self.ev2).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 50,
                'donation_count': 1,
                'donation_max': 50,
                'donation_avg': 50,
                'donation_med': 50,
            },
            models.DonorCache.objects.get(donor=None, event=self.ev3).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 65,
                'donation_count': 5,
                'donation_max': 25,
                'donation_avg': 13,
                'donation_med': 10,
            },
            models.DonorCache.objects.get(donor=None, currency='USD').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 50,
                'donation_count': 1,
                'donation_max': 50,
                'donation_avg': 50,
                'donation_med': 50,
            },
            models.DonorCache.objects.get(donor=None, currency='EUR').__dict__,
        )
        # now change them all to pending to make sure the delete logic for that
        # works
        d2.transactionstate = 'PENDING'
        d2.save()
        self.assertDictContainsSubset(
            {
                'donation_total': 5,
                'donation_count': 1,
                'donation_max': 5,
                'donation_avg': 5,
                'donation_med': 5,
            },
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 15,
                'donation_count': 2,
                'donation_max': 10,
                'donation_avg': 7.5,
                'donation_med': 7.5,
            },
            models.DonorCache.objects.get(donor=self.john, currency='USD').__dict__,
        )
        d1.transactionstate = 'PENDING'
        d1.save()
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, event=self.ev1).exists()
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 10,
                'donation_count': 1,
                'donation_max': 10,
                'donation_avg': 10,
                'donation_med': 10,
            },
            models.DonorCache.objects.get(donor=self.john, currency='USD').__dict__,
        )
        d3.transactionstate = 'PENDING'
        d3.save()
        self.assertFalse(models.DonorCache.objects.filter(donor=self.john).exists())
        d4.delete()  # delete the last of it to make sure it's all gone
        d5.delete()
        d6.delete()
        self.assertFalse(0, models.DonorCache.objects.exists())


class TestDonorEmailSave(TestCase):
    def testSaveWithExistingDoesNotThrow(self):
        rand = random.Random(None)
        d1 = randgen.generate_donor(rand)
        d1.paypalemail = d1.email
        d1.clean()
        d1.save()
        d1.clean()


class TestDonorMerge(TestCase):
    def testBasicMerge(self):
        rand = random.Random(None)
        randgen.build_random_event(rand, num_donors=10, num_donations=20, num_runs=10)
        donorList = models.Donor.objects.all()
        rootDonor = donorList[0]
        donationList = []
        for donor in donorList:
            donationList.extend(donor.donation_set.all())
        viewutil.merge_donors(rootDonor, donorList)
        for donor in donorList[1:]:
            self.assertFalse(models.Donor.objects.filter(id=donor.id).exists())
        self.assertEqual(len(donationList), rootDonor.donation_set.count())
        for donation in rootDonor.donation_set.all():
            self.assertTrue(donation in donationList)


@skip('currently disabled')
class TestDonorView(TestCase):
    def setUp(self):
        super(TestDonorView, self).setUp()
        self.event = models.Event.objects.create(
            name='test', datetime=today_noon, short='test'
        )
        self.other_event = models.Event.objects.create(
            name='test2', datetime=tomorrow_noon, short='test2'
        )

    def set_donor(self, firstname='John', lastname='Doe', **kwargs):
        self.donor, created = models.Donor.objects.get_or_create(
            firstname=firstname, lastname=lastname, defaults=kwargs
        )
        if not created:
            for k, v in kwargs.items():
                setattr(self.donor, k, v)
            if kwargs:
                self.donor.save()

    def test_normal_visibility_cases(self):
        for visibility in ['FULL', 'FIRST', 'ALIAS']:
            self.set_donor(alias='JDoe %s' % visibility, visibility=visibility)
            models.Donation.objects.get_or_create(
                donor=self.donor,
                event=self.event,
                amount=5,
            )
            donor_header = (
                f'<h2 class="text-center">{self.donor.full_visible_name}</h2>'
            )
            resp = self.client.get(reverse('tracker:donor', args=(self.donor.id,)))
            self.assertContains(resp, donor_header, html=True)
            self.assertNotContains(resp, 'Invalid Variable')
            resp = self.client.get(
                reverse('tracker:donor', args=(self.donor.id, self.event.id))
            )
            self.assertContains(resp, donor_header, html=True)
            self.assertNotContains(resp, 'Invalid Variable')
            resp = self.client.get(
                reverse('tracker:donor', args=(self.donor.id, self.other_event.id))
            )
            self.assertEqual(resp.status_code, 404)

    def test_anonymous_donor(self):
        self.set_donor(visibility='ANON')
        models.Donation.objects.create(donor=self.donor, event=self.event, amount=5)
        resp = self.client.get(reverse('tracker:donor', args=(self.donor.id,)))
        self.assertEqual(resp.status_code, 404)


class TestDonorAlias(TestCase):
    def test_alias_num_missing(self):
        donor = models.Donor.objects.create(alias='Raelcun')
        self.assertNotEqual(donor.alias_num, None, msg='Alias number was not filled in')

    def test_alias_num_cleared(self):
        donor = models.Donor.objects.create(alias='Raelcun', alias_num=1000)
        donor.alias = None
        donor.save()
        self.assertEqual(donor.alias_num, None, msg='Alias number was not cleared')

    def test_alias_num_no_duplicates(self):
        # degenerate case, create everything BUT 9999
        for i in range(1000, 9999):
            models.Donor.objects.create(alias='Raelcun', alias_num=i)
        donor = models.Donor.objects.create(alias='Raelcun')
        self.assertEqual(donor.alias_num, 9999, msg='degenerate case did not work')

    def test_alias_truly_degenerate(self):
        # fill in ALL the holes
        for i in range(1000, 10000):
            models.Donor.objects.create(alias='Raelcun', alias_num=i)
        with self.assertLogs(level=logging.WARNING) as logs:
            donor = models.Donor.objects.create(alias='Raelcun')
        self.assertRegex(logs.output[0], 'namespace was full')
        self.assertEqual(donor.alias, None, msg='Alias was not cleared')
        self.assertEqual(donor.alias_num, None, msg='Alias was not cleared')


class TestDonorAliasMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0010_add_alias_num')]
    migrate_to = [('tracker', '0011_backfill_alias')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Donation = apps.get_model('tracker', 'Donation')
        Donor = apps.get_model('tracker', 'Donor')

        event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon
        )
        self.event_id = event.id
        donor = Donor.objects.create(alias='bar')
        self.donor_id = donor.id
        self.other_donor_id = Donor.objects.create(alias='baz').id
        self.donation_id = Donation.objects.create(
            event=event,
            amount=5,
            requestedalias=' foo ',
            donor=donor,
            domainId='deadbeaf',
            transactionstate='COMPLETED',
            timereceived=today_noon,
        ).id
        self.other_donation_id = Donation.objects.create(
            event=event,
            amount=5,
            requestedalias=' bar ',
            donor=donor,
            domainId='deadbead',
            transactionstate='COMPLETED',
            timereceived=long_ago_noon,
        ).id

    def test_whitespace_with_alias(self):
        Donation = self.apps.get_model('tracker', 'Donation')
        self.assertEqual(
            Donation.objects.get(id=self.donation_id).requestedalias,
            'foo',
            msg='Whitespace was not stripped',
        )
        Donor = self.apps.get_model('tracker', 'Donor')
        donor = Donor.objects.get(id=self.donor_id)
        self.assertEqual(
            donor.alias, 'foo', msg='Alias was not reapplied or wrong alias was used'
        )
        self.assertNotEqual(donor.alias_num, None, msg='Alias number was not filled in')

    def test_donor_with_missing_alias_num(self):
        Donor = self.apps.get_model('tracker', 'Donor')
        donor = Donor.objects.get(id=self.other_donor_id)
        self.assertNotEqual(donor.alias_num, None, msg='Alias number was not filled in')


class TestDonorAdmin(TestCase, AssertionHelpers):
    def setUp(self):
        self.admin = admin.donation.DonorAdmin(models.Donor, AdminSite())
        self.factory = RequestFactory()
        self.super_user = User.objects.create_superuser('admin', 'admin@example.com')
        self.limited_user = User.objects.create(username='staff')
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', datetime=today_noon
        )

        self.donor = models.Donor.objects.create(firstname='John', lastname='Doe')

    def test_donor_admin(self):
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('admin:tracker_donor_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donor_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_donor_change', args=(self.donor.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_search_fields(self):
        request = self.factory.get('admin:tracker_donor_changelist')

        with self.subTest('all permissions'):
            request.user = self.super_user
            search_fields = self.admin.get_search_fields(request)
            self.assertSetEqual(
                {'email', 'paypalemail', 'alias', 'firstname', 'lastname'},
                set(search_fields),
            )

        with self.subTest('partial permissions'):
            request.user = self.limited_user
            self.limited_user.user_permissions.add(
                Permission.objects.get(codename='view_emails')
            )
            search_fields = self.admin.get_search_fields(request)
            self.assertSetEqual({'email', 'paypalemail', 'alias'}, set(search_fields))

            self.limited_user.user_permissions.set(
                [Permission.objects.get(codename='view_full_names')]
            )
            self.limited_user = User.objects.get(id=self.limited_user.id)
            request.user = self.limited_user
            search_fields = self.admin.get_search_fields(request)
            self.assertSetEqual({'firstname', 'lastname', 'alias'}, set(search_fields))

        with self.subTest('no special permissions'):
            request.user = AnonymousUser()
            search_fields = self.admin.get_search_fields(request)
            self.assertSetEqual({'alias'}, set(search_fields))


class TestDonorCacheCurrencyMigration(MigrationsTestCase, AssertionHelpers):
    migrate_from = [('tracker', '0069_donor_cache_enhancements')]
    migrate_to = [('tracker', '0070_backfill_donor_cache_enhancements')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Donation = apps.get_model('tracker', 'Donation')
        Donor = apps.get_model('tracker', 'Donor')
        DonorCache = apps.get_model('tracker', 'DonorCache')
        self.us_event_id = Event.objects.create(
            short='us', name='US', datetime=today_noon, paypalcurrency='USD'
        ).id
        self.eu_event_id = Event.objects.create(
            short='eu', name='EU', datetime=long_ago_noon, paypalcurrency='EUR'
        ).id
        self.empty_event_id = Event.objects.create(
            short='empty', name='Empty', datetime=tomorrow_noon, paypalcurrency='EUR'
        ).id
        self.donor1_id = Donor.objects.create().id
        self.donor2_id = Donor.objects.create().id
        Donation.objects.create(
            event_id=self.us_event_id,
            amount=5,
            transactionstate='COMPLETED',
            donor_id=self.donor1_id,
            domainId='deadbeef',
        )
        Donation.objects.create(
            event_id=self.us_event_id,
            amount=25,
            transactionstate='COMPLETED',
            donor_id=self.donor1_id,
            domainId='deedbeef',
        )
        Donation.objects.create(
            event_id=self.us_event_id,
            amount=10,
            transactionstate='COMPLETED',
            donor_id=self.donor2_id,
            domainId='deafbeef',
        )
        Donation.objects.create(
            event_id=self.eu_event_id,
            amount=20,
            transactionstate='COMPLETED',
            donor_id=self.donor1_id,
            domainId='feedbeef',
        )
        # should be deleted
        DonorCache.objects.create(donor_id=self.donor1_id, event=None)

    def test_currency_split(self):
        DonorCache = self.apps.get_model('tracker', 'DonorCache')
        self.assertEqual(
            DonorCache.objects.filter(donor_id=self.donor1_id, event=None).count(), 2
        )
        self.assertEqual(
            DonorCache.objects.filter(donor_id=self.donor2_id, event=None).count(), 1
        )
        self.assertDictContainsSubset(
            {
                'donation_count': 2,
                'donation_total': 30,
                'donation_max': 25,
                'donation_avg': 15,
                'donation_med': 15,
            },
            DonorCache.objects.get(donor_id=self.donor1_id, currency='USD').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_count': 1,
                'donation_total': 20,
                'donation_max': 20,
                'donation_avg': 20,
                'donation_med': 20,
            },
            DonorCache.objects.get(donor_id=self.donor1_id, currency='EUR').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_count': 1,
                'donation_total': 10,
                'donation_max': 10,
                'donation_avg': 10,
                'donation_med': 10,
            },
            DonorCache.objects.get(donor_id=self.donor2_id, currency='USD').__dict__,
        )
        self.assertFalse(
            DonorCache.objects.filter(event_id=self.empty_event_id).exists()
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 40,
                'donation_count': 3,
                'donation_max': 25,
                'donation_avg': Decimal(40.0 / 3).quantize(Decimal('0.00')),
                'donation_med': 10,
            },
            DonorCache.objects.get(donor=None, event_id=self.us_event_id).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 20,
                'donation_count': 1,
                'donation_max': 20,
                'donation_avg': 20,
                'donation_med': 20,
            },
            DonorCache.objects.get(donor=None, event_id=self.eu_event_id).__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 40,
                'donation_count': 3,
                'donation_max': 25,
                'donation_avg': Decimal(40.0 / 3).quantize(Decimal('0.00')),
                'donation_med': 10,
            },
            DonorCache.objects.get(donor=None, event=None, currency='USD').__dict__,
        )
        self.assertDictContainsSubset(
            {
                'donation_total': 20,
                'donation_count': 1,
                'donation_max': 20,
                'donation_avg': 20,
                'donation_med': 20,
            },
            DonorCache.objects.get(donor=None, event=None, currency='EUR').__dict__,
        )
