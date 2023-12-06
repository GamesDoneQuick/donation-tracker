import logging
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker import models, viewutil

from . import randgen
from .util import MigrationsTestCase, long_ago_noon, today_noon, tomorrow_noon


class TestDonorTotals(TestCase):
    def setUp(self):
        self.john = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com'
        )
        self.jane = models.Donor.objects.create(
            firstname='Jane', lastname='Doe', email='janedoe@example.com'
        )
        self.ev1 = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon
        )
        self.ev2 = models.Event.objects.create(
            short='ev2', name='Event 2', targetamount=5, datetime=today_noon
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
        self.assertEqual(2, models.DonorCache.objects.count())
        d2 = models.Donation.objects.create(
            donor=self.john,
            event=self.ev2,
            amount=5,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        self.assertEqual(3, models.DonorCache.objects.count())
        d3 = models.Donation.objects.create(
            donor=self.john,
            event=self.ev2,
            amount=10,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        self.assertEqual(3, models.DonorCache.objects.count())
        d4 = models.Donation.objects.create(
            donor=self.jane,
            event=self.ev1,
            amount=20,
            domain='PAYPAL',
            transactionstate='COMPLETED',
        )
        self.assertEqual(5, models.DonorCache.objects.count())
        self.assertEqual(
            5,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev1
            ).donation_total,
        )
        self.assertEqual(
            1,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev1
            ).donation_count,
        )
        self.assertEqual(
            5,
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).donation_max,
        )
        self.assertEqual(
            5,
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).donation_avg,
        )
        self.assertEqual(
            15,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev2
            ).donation_total,
        )
        self.assertEqual(
            2,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev2
            ).donation_count,
        )
        self.assertEqual(
            10,
            models.DonorCache.objects.get(donor=self.john, event=self.ev2).donation_max,
        )
        self.assertEqual(
            7.5,
            models.DonorCache.objects.get(donor=self.john, event=self.ev2).donation_avg,
        )
        self.assertEqual(
            20,
            models.DonorCache.objects.get(donor=self.john, event=None).donation_total,
        )
        self.assertEqual(
            3, models.DonorCache.objects.get(donor=self.john, event=None).donation_count
        )
        self.assertEqual(
            10, models.DonorCache.objects.get(donor=self.john, event=None).donation_max
        )
        self.assertAlmostEqual(
            Decimal(20 / 3.0),
            models.DonorCache.objects.get(donor=self.john, event=None).donation_avg,
            2,
        )
        self.assertEqual(
            20,
            models.DonorCache.objects.get(
                donor=self.jane, event=self.ev1
            ).donation_total,
        )
        self.assertEqual(
            1,
            models.DonorCache.objects.get(
                donor=self.jane, event=self.ev1
            ).donation_count,
        )
        self.assertEqual(
            20,
            models.DonorCache.objects.get(donor=self.jane, event=self.ev1).donation_max,
        )
        self.assertEqual(
            20,
            models.DonorCache.objects.get(donor=self.jane, event=self.ev1).donation_avg,
        )
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.jane, event=self.ev2).exists()
        )
        self.assertEqual(
            20,
            models.DonorCache.objects.get(donor=self.jane, event=None).donation_total,
        )
        self.assertEqual(
            1, models.DonorCache.objects.get(donor=self.jane, event=None).donation_count
        )
        self.assertEqual(
            20, models.DonorCache.objects.get(donor=self.jane, event=None).donation_max
        )
        self.assertEqual(
            20, models.DonorCache.objects.get(donor=self.jane, event=None).donation_avg
        )
        # now change them all to pending to make sure the delete logic for that
        # works
        d2.transactionstate = 'PENDING'
        d2.save()
        self.assertEqual(
            5,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev1
            ).donation_total,
        )
        self.assertEqual(
            1,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev1
            ).donation_count,
        )
        self.assertEqual(
            5,
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).donation_max,
        )
        self.assertEqual(
            5,
            models.DonorCache.objects.get(donor=self.john, event=self.ev1).donation_avg,
        )
        self.assertEqual(
            10,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev2
            ).donation_total,
        )
        self.assertEqual(
            1,
            models.DonorCache.objects.get(
                donor=self.john, event=self.ev2
            ).donation_count,
        )
        self.assertEqual(
            10,
            models.DonorCache.objects.get(donor=self.john, event=self.ev2).donation_max,
        )
        self.assertEqual(
            10,
            models.DonorCache.objects.get(donor=self.john, event=self.ev2).donation_avg,
        )
        self.assertEqual(
            15,
            models.DonorCache.objects.get(donor=self.john, event=None).donation_total,
        )
        self.assertEqual(
            2, models.DonorCache.objects.get(donor=self.john, event=None).donation_count
        )
        self.assertEqual(
            10, models.DonorCache.objects.get(donor=self.john, event=None).donation_max
        )
        self.assertAlmostEqual(
            Decimal(15 / 2.0),
            models.DonorCache.objects.get(donor=self.john, event=None).donation_avg,
            2,
        )
        d1.transactionstate = 'PENDING'
        d1.save()
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, event=self.ev1).exists()
        )
        self.assertEqual(
            10,
            models.DonorCache.objects.get(donor=self.john, event=None).donation_total,
        )
        self.assertEqual(
            1, models.DonorCache.objects.get(donor=self.john, event=None).donation_count
        )
        self.assertEqual(
            10, models.DonorCache.objects.get(donor=self.john, event=None).donation_max
        )
        self.assertEqual(
            10, models.DonorCache.objects.get(donor=self.john, event=None).donation_avg
        )
        d3.transactionstate = 'PENDING'
        d3.save()
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, event=self.ev2).exists()
        )
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.john, event=None).exists()
        )
        self.assertEqual(
            2, models.DonorCache.objects.count()
        )  # jane's stuff still exists
        d4.delete()  # delete the last of it to make sure it's all gone
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.jane, event=self.ev1).exists()
        )
        self.assertFalse(
            models.DonorCache.objects.filter(donor=self.jane, event=None).exists()
        )
        self.assertEqual(0, models.DonorCache.objects.count())


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


class TestDonorView(TestCase):
    def setUp(self):
        super(TestDonorView, self).setUp()
        self.event = models.Event.objects.create(
            name='test', targetamount=10, datetime=today_noon, short='test'
        )
        self.other_event = models.Event.objects.create(
            name='test2', targetamount=10, datetime=tomorrow_noon, short='test2'
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
                f'<h2 class="text-center">{self.donor.full_visible_name()}</h2>'
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
        self.assertRegexpMatches(logs.output[0], 'namespace was full')
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


class TestDonorAdmin(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon
        )

        self.donor = models.Donor.objects.create(firstname='John', lastname='Doe')

    def test_donor_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_donor_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donor_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_donor_change', args=(self.donor.id,))
        )
        self.assertEqual(response.status_code, 200)
