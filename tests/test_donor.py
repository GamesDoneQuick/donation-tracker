import tracker.models as models
import tracker.randgen as randgen
import tracker.forms as forms
import tracker.viewutil as viewutil

from django.test import TestCase, TransactionTestCase

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
