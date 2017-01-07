from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from .. import models, views, randgen, viewutil
from ..templatetags.donation_tags import donor_link

from django.test import TransactionTestCase
from django import template

from decimal import Decimal
import random
import datetime
import pytz


class TestDonorTotals(TransactionTestCase):

    def setUp(self):
        self.john = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com')
        self.jane = models.Donor.objects.create(
            firstname='Jane', lastname='Doe', email='janedoe@example.com')
        self.ev1 = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, date=datetime.date.today())
        self.ev2 = models.Event.objects.create(
            short='ev2', name='Event 2', targetamount=5, date=datetime.date.today())

    def test_donor_cache(self):
        self.assertEqual(0, models.DonorCache.objects.count())
        d1 = models.Donation.objects.create(donor=self.john, event=self.ev1, amount=5, domainId='d1',
                                            transactionstate='COMPLETED', timereceived=datetime.datetime.now(pytz.utc))
        self.assertEqual(2, models.DonorCache.objects.count())
        d2 = models.Donation.objects.create(donor=self.john, event=self.ev2, amount=5, domainId='d2',
                                            transactionstate='COMPLETED', timereceived=datetime.datetime.now(pytz.utc))
        self.assertEqual(3, models.DonorCache.objects.count())
        d3 = models.Donation.objects.create(donor=self.john, event=self.ev2, amount=10, domainId='d3',
                                            transactionstate='COMPLETED', timereceived=datetime.datetime.now(pytz.utc))
        self.assertEqual(3, models.DonorCache.objects.count())
        d4 = models.Donation.objects.create(donor=self.jane, event=self.ev1, amount=20, domainId='d4',
                                            transactionstate='COMPLETED', timereceived=datetime.datetime.now(pytz.utc))
        self.assertEqual(5, models.DonorCache.objects.count())
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_count)
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_max)
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_avg)
        self.assertEqual(15, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_total)
        self.assertEqual(2, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_count)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_max)
        self.assertEqual(7.5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_avg)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_total)
        self.assertEqual(3, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_count)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_max)
        self.assertAlmostEqual(Decimal(
            20 / 3.0), models.DonorCache.objects.get(donor=self.john, event=None).donation_avg, 2)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=self.ev1).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.jane, event=self.ev1).donation_count)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=self.ev1).donation_max)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=self.ev1).donation_avg)
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.jane, event=self.ev2).exists())
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=None).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.jane, event=None).donation_count)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=None).donation_max)
        self.assertEqual(20, models.DonorCache.objects.get(
            donor=self.jane, event=None).donation_avg)
        # now change them all to pending to make sure the delete logic for that
        # works
        d2.transactionstate = 'PENDING'
        d2.save()
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_count)
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_max)
        self.assertEqual(5, models.DonorCache.objects.get(
            donor=self.john, event=self.ev1).donation_avg)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_count)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_max)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=self.ev2).donation_avg)
        self.assertEqual(15, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_total)
        self.assertEqual(2, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_count)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_max)
        self.assertAlmostEqual(Decimal(
            15 / 2.0), models.DonorCache.objects.get(donor=self.john, event=None).donation_avg, 2)
        d1.transactionstate = 'PENDING'
        d1.save()
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.john, event=self.ev1).exists())
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_total)
        self.assertEqual(1, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_count)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_max)
        self.assertEqual(10, models.DonorCache.objects.get(
            donor=self.john, event=None).donation_avg)
        d3.transactionstate = 'PENDING'
        d3.save()
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.john, event=self.ev2).exists())
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.john, event=None).exists())
        self.assertEqual(2, models.DonorCache.objects.count()
                         )  # jane's stuff still exists
        d4.delete()  # delete the last of it to make sure it's all gone
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.jane, event=self.ev1).exists())
        self.assertFalse(models.DonorCache.objects.filter(
            donor=self.jane, event=None).exists())
        self.assertEqual(0, models.DonorCache.objects.count())


class TestDonorEmailSave(TransactionTestCase):

    def testSaveWithExistingDoesNotThrow(self):
        rand = random.Random(None)
        d1 = randgen.generate_donor(rand)
        d1.paypalemail = d1.email
        d1.clean()
        d1.save()
        d1.clean()


class TestDonorMerge(TransactionTestCase):

    def testBasicMerge(self):
        rand = random.Random(None)
        ev = randgen.build_random_event(
            rand, numDonors=10, numDonations=20, numRuns=10)
        donorList = models.Donor.objects.all()
        rootDonor = donorList[0]
        donationList = []
        for donor in donorList:
            donationList.extend(list(donor.donation_set.all()))
        result = viewutil.merge_donors(rootDonor, donorList)
        for donor in donorList[1:]:
            self.assertFalse(models.Donor.objects.filter(id=donor.id).exists())
        self.assertEquals(len(donationList), rootDonor.donation_set.count())
        for donation in rootDonor.donation_set.all():
            self.assertTrue(donation in donationList)

class TestDonorLink(TransactionTestCase):
    def test_normal_cases(self):
        for visibility in ['FULL', 'FIRST', 'ALIAS']:
            donor = models.Donor.objects.create(firstname='John', lastname='Doe', alias='JDoe', visibility=visibility)
            html = donor_link(template.Context(), donor)
            self.assertIn(donor.get_absolute_url(), html)
            self.assertIn(donor.visible_name(), html)

    def test_with_event(self):
        donor = models.Donor.objects.create(firstname='John', lastname='Doe', alias='JDoe', visibility='ANON')
        event = models.Event.objects.create(name='test', targetamount=10, date=datetime.date.today())
        html = donor_link(template.Context(), donor, event)
        self.assertNotIn(donor.get_absolute_url(event), html)
        self.assertIn(donor.visible_name(), html)

    def test_anonymous_donor(self):
        donor = models.Donor.objects.create(firstname='John', lastname='Doe', alias='JDoe', visibility='ANON')
        html = donor_link(template.Context(), donor)
        self.assertNotIn(donor.get_absolute_url(), html)
        self.assertIn(donor.visible_name(), html)

class TestDonorView(TransactionTestCase):
    def setUp(self):
        super(TestDonorView, self).setUp()
        self.factory = RequestFactory()
        self.event = models.Event.objects.create(name='test', targetamount=10, date=datetime.date.today())

    def set_donor(self, firstname='John', lastname='Doe', **kwargs):
        self.donor, created = models.Donor.objects.get_or_create(
            firstname=firstname,
            lastname=lastname,
            defaults=kwargs)
        if not created:
            for k,v in kwargs.items():
                setattr(self.donor, k, v)
            if kwargs:
                self.donor.save()

    def test_normal_visibility_cases(self):
        for visibility in ['FULL', 'FIRST', 'ALIAS']:
            self.set_donor(alias='JDoe %s' % visibility, visibility=visibility)
            models.Donation.objects.get_or_create(donor=self.donor, event=self.event, amount=5, transactionstate='COMPLETED')
            request = self.factory.get(self.donor.get_absolute_url())
            request.user = AnonymousUser()
            self.assertEqual(views.donor(request, self.donor.id).status_code, 200)

    def test_anonymous_donor(self):
        self.set_donor(visibility='ANON')
        models.Donation.objects.create(donor=self.donor, event=self.event, amount=5, transactionstate='COMPLETED')
        request = self.factory.get(self.donor.get_absolute_url())
        request.user = AnonymousUser()
        self.assertEqual(views.donor(request, self.donor.id).status_code, 404)
