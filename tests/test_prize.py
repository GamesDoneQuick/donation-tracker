import datetime
import random
from decimal import Decimal

import pytz
from dateutil.parser import parse as parse_date
from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from .. import models, prizeutil, randgen
from . import MigrationsTestCase

noon = datetime.time(12, 0)
today = datetime.date.today()
today_noon = datetime.datetime.combine(today, noon)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon)


class TestRemoveNullsMigrations(MigrationsTestCase):
    migrate_from = '0007_add_prize_key'
    migrate_to = '0008_remove_prize_nulls'

    def setUpBeforeMigration(self, apps):
        Prize = apps.get_model('tracker', 'Prize')
        Event = apps.get_model('tracker', 'Event')
        self.event = Event.objects.create(short='test', name='Test Event', datetime=today_noon, targetamount=100)
        self.prize1 = Prize.objects.create(event=self.event, name='Test Prize')

    def test_nulls_removed(self):
        self.prize1.refresh_from_db()
        self.assertEqual(self.prize1.altimage, '')
        self.assertEqual(self.prize1.description, '')
        self.assertEqual(self.prize1.extrainfo, '')
        self.assertEqual(self.prize1.image, '')


class TestPrizeDrawingGeneratedEvent(TransactionTestCase):

    def setUp(self):
        self.eventStart = parse_date(
            "2014-01-01 16:00:00").replace(tzinfo=pytz.utc)
        self.rand = random.Random(516273)
        self.event = randgen.build_random_event(
            self.rand, self.eventStart, numDonors=100, numRuns=50)
        self.runsList = list(models.SpeedRun.objects.filter(event=self.event))
        self.donorList = list(models.Donor.objects.all())

    def test_draw_random_prize_no_donations(self):
        prizeList = randgen.generate_prizes(
            self.rand, self.event, 50, self.runsList)
        for prize in prizeList:
            for randomness in [True, False]:
                for useSum in [True, False]:
                    prize.randomdraw = randomness
                    prize.sumdonations = useSum
                    prize.save()
                    eligibleDonors = prize.eligible_donors()
                    self.assertEqual(0, len(eligibleDonors))
                    result, message = prizeutil.draw_prize(prize)
                    self.assertFalse(result)
                    self.assertEqual(0, prize.current_win_count())

    def test_draw_prize_one_donor(self):
        for useRandom in [True, False]:
            for useSum in [True, False]:
                for donationSize in ['top', 'bottom', 'above', 'below', 'within']:
                    prize = randgen.generate_prize(
                        self.rand, event=self.event, sumDonations=useSum, randomDraw=useRandom)
                    prize.save()
                    donor = randgen.pick_random_element(
                        self.rand, self.donorList)
                    donation = randgen.generate_donation(
                        self.rand, donor=donor, event=self.event, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
                    if donationSize == 'above':
                        donation.amount = prize.maximumbid + Decimal('5.00')
                    elif donationSize == 'top':
                        donation.amount = prize.maximumbid
                    elif donationSize == 'within':
                        donation.amount = randgen.random_amount(
                            self.rand, rounded=False, minAmount=prize.minimumbid, maxAmount=prize.maximumbid)
                    elif donationSize == 'bottom':
                        donation.amount = prize.minimumbid
                    elif donationSize == 'below':
                        donation.amount = max(
                            Decimal('0.00'), prize.minimumbid - Decimal('5.00'))
                    donation.save()
                    eligibleDonors = prize.eligible_donors()
                    if donationSize == 'below' and prize.randomdraw:
                        self.assertEqual(0, len(eligibleDonors))
                    else:
                        self.assertEqual(1, len(eligibleDonors))
                        self.assertEqual(donor.id, eligibleDonors[0]['donor'])
                        self.assertEqual(
                            donation.amount, eligibleDonors[0]['amount'])
                        if prize.sumdonations and prize.randomdraw:
                            if donationSize == 'top' or donationSize == 'above':
                                expectedRatio = float(
                                    prize.maximumbid / prize.minimumbid)
                            else:
                                expectedRatio = float(
                                    donation.amount / prize.minimumbid)
                            self.assertAlmostEqual(
                                expectedRatio, eligibleDonors[0]['weight'])
                        else:
                            self.assertEqual(1.0, eligibleDonors[0]['weight'])
                    result, message = prizeutil.draw_prize(prize)
                    if donationSize != 'below' or not prize.randomdraw:
                        self.assertTrue(result)
                        self.assertEqual(donor, prize.get_winner())
                    else:
                        self.assertFalse(result)
                        self.assertEqual(None, prize.get_winner())
                    donation.delete()
                    prize.prizewinner_set.all().delete()
                    prize.delete()

    def test_draw_prize_multiple_donors_random_nosum(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=False, randomDraw=True,
            startTime=self.eventStart, endTime=self.eventStart + datetime.timedelta(hours=2))
        prize.save()
        donationDonors = {}
        for donor in self.donorList:
            if self.rand.getrandbits(1) == 0:
                donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid,
                                                     maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
                donation.save()
                donationDonors[donor.id] = donor
            # Add a few red herrings to make sure out of range donations aren't
            # used
            donation2 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid,
                                                  maxAmount=prize.minimumbid + Decimal('100.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
            donation2.save()
            donation3 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid,
                                                  maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
            donation3.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(len(donationDonors.keys()), len(eligibleDonors))
        for eligibleDonor in eligibleDonors:
            found = False
            if eligibleDonor['donor'] in donationDonors:
                donor = donationDonors[eligibleDonor['donor']]
                donation = donor.donation_set.filter(timereceived__gte=prize.start_draw_time(
                ), timereceived__lte=prize.end_draw_time())[0]
                self.assertEqual(donation.amount, eligibleDonor['amount'])
                self.assertEqual(1.0, eligibleDonor['weight'])
                found = True
            self.assertTrue(found and "Could not find the donor in the list")
        winners = []
        for seed in [15634, 12512, 666]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winner().id, donationDonors)
            winners.append(prize.get_winner())
            current = prize.get_winner()
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(current, prize.get_winner())
            prize.prizewinner_set.all().delete()
            prize.save()
        self.assertNotEqual(winners[0], winners[1])
        self.assertNotEqual(winners[1], winners[2])
        self.assertNotEqual(winners[0], winners[2])

    def test_draw_prize_multiple_donors_random_sum(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True,
            startTime=self.eventStart, endTime=self.eventStart + datetime.timedelta(hours=2))
        prize.save()
        donationDonors = {}
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            donationDonors[donor.id] = {
                'donor': donor, 'amount': Decimal('0.00')}
            for i in range(0, numDonations):
                donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                    '0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
                donation.save()
                donationDonors[donor.id]['amount'] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
                else:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
                donation.save()
            if donationDonors[donor.id]['amount'] < prize.minimumbid:
                del donationDonors[donor.id]
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(len(donationDonors.keys()), len(eligibleDonors))
        for eligibleDonor in eligibleDonors:
            found = False
            if eligibleDonor['donor'] in donationDonors:
                entry = donationDonors[eligibleDonor['donor']]
                donor = entry['donor']
                if entry['amount'] >= prize.minimumbid:
                    donations = donor.donation_set.filter(
                        timereceived__gte=prize.start_draw_time(), timereceived__lte=prize.end_draw_time())
                    countAmount = Decimal('0.00')
                    for donation in donations:
                        countAmount += donation.amount
                    self.assertEqual(entry['amount'], eligibleDonor['amount'])
                    self.assertEqual(countAmount, eligibleDonor['amount'])
                    self.assertAlmostEqual(min(prize.maximumbid / prize.minimumbid, entry[
                                           'amount'] / prize.minimumbid), Decimal(eligibleDonor['weight']))
                    found = True
        self.assertTrue(found and "Could not find the donor in the list")
        winners = []
        for seed in [51234, 235426, 62363245]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winner().id, donationDonors)
            winners.append(prize.get_winner())
            current = prize.get_winner()
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(current, prize.get_winner())
            prize.prizewinner_set.all().delete()
            prize.save()
        self.assertNotEqual(winners[0], winners[1])
        self.assertNotEqual(winners[1], winners[2])
        self.assertNotEqual(winners[0], winners[2])

    def test_draw_prize_multiple_donors_norandom_nosum(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=False, randomDraw=False,
            startTime=self.eventStart, endTime=self.eventStart + datetime.timedelta(hours=2))
        prize.save()
        largestDonor = None
        largestAmount = Decimal('0.00')
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            for i in range(0, numDonations):
                donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                    '0.01'), maxAmount=Decimal('1000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
                donation.save()
                if donation.amount > largestAmount:
                    largestDonor = donor
                    largestAmount = donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
                else:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
                donation.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(largestDonor.id, eligibleDonors[0]['donor'])
        self.assertEqual(1.0, eligibleDonors[0]['weight'])
        self.assertEqual(largestAmount, eligibleDonors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(largestDonor.id, prize.get_winner().id)
        newDonor = randgen.generate_donor(self.rand)
        newDonor.save()
        newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=Decimal(
            '1000.01'), maxAmount=Decimal('2000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        newDonation.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(newDonor.id, eligibleDonors[0]['donor'])
        self.assertEqual(1.0, eligibleDonors[0]['weight'])
        self.assertEqual(newDonation.amount, eligibleDonors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(newDonor.id, prize.get_winner().id)

    def test_draw_prize_multiple_donors_norandom_sum(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=False,
            startTime=self.eventStart, endTime=self.eventStart + datetime.timedelta(hours=2))
        prize.save()
        donationDonors = {}
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            donationDonors[donor.id] = {
                'donor': donor, 'amount': Decimal('0.00')}
            for i in range(0, numDonations):
                donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                    '0.01'), maxAmount=Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
                donation.save()
                donationDonors[donor.id]['amount'] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
                else:
                    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal(
                        '1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
                donation.save()
        maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1]
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor'])
        self.assertEqual(1.0, eligibleDonors[0]['weight'])
        self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(maxDonor['donor'].id, prize.get_winner().id)
        oldMaxDonor = maxDonor
        del donationDonors[oldMaxDonor['donor'].id]
        maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1]
        diff = oldMaxDonor['amount'] - maxDonor['amount']
        newDonor = maxDonor['donor']
        newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=diff + Decimal(
            '0.01'), maxAmount=diff + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        newDonation.save()
        maxDonor['amount'] += newDonation.amount
        prize = models.Prize.objects.get(id=prize.id)
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor'])
        self.assertEqual(1.0, eligibleDonors[0]['weight'])
        self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(maxDonor['donor'].id, prize.get_winner().id)


class TestDonorPrizeEntryDraw(TransactionTestCase):

    def setUp(self):
        self.rand = random.Random(9239234)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    def testSingleEntry(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        entry = models.DonorPrizeEntry(donor=donor, prize=prize)
        entry.save()
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))
        self.assertEqual(donor.pk, eligible[0]['donor'])
        self.assertEqual(entry.weight, eligible[0]['weight'])

    def testMultipleEntries(self):
        numDonors = 5
        donors = []
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        for i in range(0, numDonors):
            donor = randgen.generate_donor(self.rand)
            donor.save()
            entry = models.DonorPrizeEntry(donor=donor, prize=prize)
            entry.save()
            donors.append(donor.pk)
        eligible = prize.eligible_donors()
        self.assertEqual(numDonors, len(eligible))
        for donorId in map(lambda x: x['donor'], eligible):
            self.assertTrue(donorId in donors)


class TestPrizeMultiWin(TransactionTestCase):

    def setUp(self):
        self.eventStart = parse_date("2012-01-01 01:00:00")
        self.rand = random.Random()
        self.event = randgen.build_random_event(
            self.rand, startTime=self.eventStart)
        self.event.save()

    def testWinMultiPrize(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 3
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result, msg)
        prizeWinner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEquals(1, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result, msg)
        prizeWinner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEquals(2, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result, msg)
        prizeWinner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEquals(3, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result, msg)

    def testWinMultiPrizeWithAccept(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 3
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prizeWinner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, acceptcount=1)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prizeWinner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEquals(2, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)

    def testWinMultiPrizeWithDeny(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 3
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prizeWinner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, declinecount=1)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prizeWinner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEquals(2, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)

    def testWinMultiPrizeLowerThanMaxWin(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 2
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prizeWinner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, declinecount=1)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)
        donor2 = randgen.generate_donor(self.rand)
        donor2.save()
        models.DonorPrizeEntry.objects.create(donor=donor2, prize=prize)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prizeWinner = models.PrizeWinner.objects.get(
            winner=donor2, prize=prize)
        self.assertEquals(1, prizeWinner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)


class TestPersistentPrizeWinners(TransactionTestCase):

    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
    # checks that a prize with a single eligible winner keeps track of a
    # declined prize, and disallows that person from being drawn again

    def test_decline_prize_single(self):
        amount = Decimal('50.0')
        targetPrize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=False, randomDraw=False, minAmount=amount, maxAmount=amount, maxwinners=1)
        targetPrize.save()
        self.assertEqual(0, len(targetPrize.eligible_donors()))
        donorA = randgen.generate_donor(self.rand)
        donorA.save()
        donorB = randgen.generate_donor(self.rand)
        donorB.save()
        donationA = randgen.generate_donation(
            self.rand, donor=donorA, minAmount=amount, maxAmount=amount, event=self.event)
        donationA.save()
        self.assertEqual(1, len(targetPrize.eligible_donors()))
        self.assertEqual(donorA.id, targetPrize.eligible_donors()[0]['donor'])
        prizeutil.draw_prize(targetPrize)
        self.assertEqual(donorA, targetPrize.get_winner())
        self.assertEqual(0, len(targetPrize.eligible_donors()))
        donationB = randgen.generate_donation(
            self.rand, donor=donorB, minAmount=amount, maxAmount=amount, event=self.event)
        donationB.save()
        self.assertEqual(1, len(targetPrize.eligible_donors()))
        self.assertEqual(donorB.id, targetPrize.eligible_donors()[0]['donor'])
        prizeWinnerEntry = targetPrize.prizewinner_set.filter(winner=donorA)[0]
        prizeWinnerEntry.pendingcount = 0
        prizeWinnerEntry.declinecount = 1
        prizeWinnerEntry.save()
        self.assertEqual(1, len(targetPrize.eligible_donors()))
        self.assertEqual(donorB.id, targetPrize.eligible_donors()[0]['donor'])
        prizeutil.draw_prize(targetPrize)
        self.assertEqual(donorB, targetPrize.get_winner())
        self.assertEqual(1, targetPrize.current_win_count())
        self.assertEqual(0, len(targetPrize.eligible_donors()))

    def test_cannot_exceed_max_winners(self):
        targetPrize = randgen.generate_prize(self.rand, event=self.event)
        targetPrize.maxwinners = 2
        targetPrize.save()
        numDonors = 4
        donors = []
        for i in range(0, numDonors):
            donor = randgen.generate_donor(self.rand)
            donor.save()
            donors.append(donor)
        pw0 = models.PrizeWinner(winner=donors[0], prize=targetPrize)
        pw0.clean()
        pw0.save()
        pw1 = models.PrizeWinner(winner=donors[1], prize=targetPrize)
        pw1.clean()
        pw1.save()
        with self.assertRaises(ValidationError):
            pw2 = models.PrizeWinner(winner=donors[2], prize=targetPrize)
            pw2.clean()
        pw0.pendingcount = 0
        pw0.declinecount = 1
        pw0.save()
        pw2.clean()
        pw2.save()


class TestPrizeCountryFilter(TransactionTestCase):
    fixtures = ['countries']

    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.build_random_event(self.rand)
        self.event.save()

    def testCountryFilterEvent(self):
        countries = list(models.Country.objects.all()[0:4])
        self.event.allowed_prize_countries.add(countries[0])
        self.event.allowed_prize_countries.add(countries[1])
        self.event.save()
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        for country in countries:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand, event=self.event, donor=donor, minAmount=Decimal(prize.minimumbid)).save()

        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        self.event.allowed_prize_countries.add(countries[3])
        self.event.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))
        # Test a blank country set
        self.event.allowed_prize_countries.clear()
        self.event.save()
        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(4, len(eligible))

    def testCountryFilterPrize(self):
        # TODO: fix this so either there's less boilerplate, or the boilerplate is shared
        countries = list(models.Country.objects.all()[0:4])
        prize = models.Prize.objects.create(event=self.event)
        for country in countries[0:3]:
            self.event.allowed_prize_countries.add(country)
        self.event.save()
        prize.allowed_prize_countries.add(countries[0])
        prize.allowed_prize_countries.add(countries[1])
        prize.save()
        donors = []
        for country in countries:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand, event=self.event, donor=donor, minAmount=Decimal(prize.minimumbid)).save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        # by default don't use the prize filter
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))

        prize.custom_country_filter = True
        prize.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        prize.allowed_prize_countries.add(countries[3])
        prize.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))
        # Test a blank country set
        prize.allowed_prize_countries.clear()
        prize.save()
        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(4, len(eligible))

    def testCountryRegionBlacklistFilterEvent(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowedState = 'StateOne'
        disallowedState = 'StateTwo'
        for state in [allowedState, disallowedState]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand, event=self.event, donor=donor, minAmount=Decimal(prize.minimumbid)).save()

        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        countryRegion = models.CountryRegion.objects.create(
            country=country, name=disallowedState)
        self.event.disallowed_prize_regions.add(countryRegion)
        self.event.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[1]))
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))

    def testCountryRegionBlacklistFilterPrize(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowedState = 'StateOne'
        disallowedState = 'StateTwo'
        for state in [allowedState, disallowedState]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand, event=self.event, donor=donor, minAmount=Decimal(prize.minimumbid)).save()

        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        countryRegion = models.CountryRegion.objects.create(
            country=country, name=disallowedState)
        prize.disallowed_prize_regions.add(countryRegion)
        prize.custom_country_filter = True
        prize.save()
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))


class TestPrizeDrawAcceptOffset(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    def test_accept_deadline_offset(self):
        # 10 days in the future
        self.event.prize_accept_deadline_delta = 10
        # TODO: it should not take this much set-up to draw a single donor to a single prize
        amount = Decimal('50.0')
        targetPrize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=False, randomDraw=False, minAmount=amount, maxAmount=amount, maxwinners=1)
        targetPrize.save()
        winner = randgen.generate_donor(self.rand)
        winner.save()
        winningDonation = randgen.generate_donation(
            self.rand, donor=winner, minAmount=amount, maxAmount=amount, event=self.event)
        winningDonation.save()
        self.assertEqual(1, len(targetPrize.eligible_donors()))
        self.assertEqual(winner.id, targetPrize.eligible_donors()[0]['donor'])
        self.assertEqual(
            0, len(prizeutil.get_past_due_prize_winners(self.event)))
        currentDate = datetime.date.today()
        result, status = prizeutil.draw_prize(targetPrize)
        prizeWin = models.PrizeWinner.objects.get(prize=targetPrize)
        self.assertEqual(prizeWin.accept_deadline_date(), currentDate +
                         datetime.timedelta(days=self.event.prize_accept_deadline_delta))

        prizeWin.acceptdeadline = datetime.datetime.utcnow().replace(
            tzinfo=pytz.utc) - datetime.timedelta(days=2)
        prizeWin.save()
        self.assertEqual(0, len(targetPrize.eligible_donors()))
        pastDue = prizeutil.get_past_due_prize_winners(self.event)
        self.assertEqual(
            1, len(prizeutil.get_past_due_prize_winners(self.event)))
        self.assertEqual(prizeWin, pastDue[0])


class TestPrizeKey(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.run = randgen.generate_run(self.rand, event=self.event)
        self.run.order = 1
        self.run.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event, randomDraw=True)
        self.prize.key_code = True
        self.prize.save()
        models.PrizeKey.objects.bulk_create(
            randgen.generate_prize_key(self.rand, prize=self.prize) for _ in range(100)
        )
        self.prize_keys = self.prize.prizekey_set.all()

    def test_leave_winners_alone_for_non_key_code(self):
        self.prize.key_code = False
        self.prize.maxwinners = 10
        self.prize.save()
        self.assertEqual(self.prize.maxwinners, 10)

    def test_set_winners_to_key_number_on_prize_save(self):
        self.assertEqual(self.prize.maxwinners, 0)
        self.prize.maxmultiwin = 5
        self.prize.save()
        self.assertEqual(self.prize.maxwinners, self.prize_keys.count())
        self.assertEqual(self.prize.maxmultiwin, 1)

    def test_set_winners_to_key_number_on_prize_key_create(self):
        self.assertEqual(self.prize.maxwinners, 0)
        self.prize_keys[0].save()  # only on create
        self.prize.refresh_from_db()
        self.assertEqual(self.prize.maxwinners, 0)
        randgen.generate_prize_key(self.rand, prize=self.prize).save()
        self.prize.refresh_from_db()
        self.assertEqual(self.prize.maxwinners, self.prize_keys.count())
        self.assertEqual(self.prize.maxmultiwin, 1)

    def test_fewer_donors_than_keys(self):
        self.prize.save()
        donors = models.Donor.objects.bulk_create([randgen.generate_donor(self.rand) for _ in range(self.prize_keys.count() / 2)])
        models.Donation.objects.bulk_create(
            [randgen.generate_donation_for_prize(self.rand, donor=d, prize=self.prize) for d in donors]
        )
        self.assertItemsEqual([d['donor'] for d in self.prize.eligible_donors()], [d.id for d in donors])
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertItemsEqual(result['winners'], [d.id for d in donors])
        self.assertItemsEqual([k.winner.id for k in self.prize_keys if k.winner], [d.id for d in donors])
        for key in self.prize_keys:
            if not key.winner:
                continue
            self.assertIn(key.winner, donors, u'%s was not in donors.' % key.winner)
            self.assertEqual(key.prize_winner.pendingcount, 0)
            self.assertEqual(key.prize_winner.acceptcount, 1)
            self.assertEqual(key.prize_winner.declinecount, 0)
            self.assertTrue(key.prize_winner.emailsent)
            self.assertEqual(key.prize_winner.acceptemailsentcount, 1)
            self.assertEqual(key.prize_winner.shippingstate, 'SHIPPED')
            self.assertFalse(key.prize_winner.shippingemailsent)

    def test_draw_with_claimed_keys(self):
        self.prize.save()
        old_donors = models.Donor.objects.bulk_create([randgen.generate_donor(self.rand) for _ in range(self.prize_keys.count() / 2)])
        old_ids = [d.id for d in old_donors]
        models.Donation.objects.bulk_create(
            [randgen.generate_donation_for_prize(self.rand, donor=d, prize=self.prize) for d in old_donors]
        )
        self.assertItemsEqual([d['donor'] for d in self.prize.eligible_donors()], [d.id for d in old_donors])
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        new_donors = models.Donor.objects.bulk_create([randgen.generate_donor(self.rand) for _ in range(self.prize_keys.count() / 2)])
        models.Donation.objects.bulk_create(
            [randgen.generate_donation_for_prize(self.rand, donor=d, prize=self.prize) for d in new_donors]
        )
        self.assertItemsEqual([d['donor'] for d in self.prize.eligible_donors()], [d.id for d in new_donors])
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertItemsEqual(result['winners'], [d.id for d in new_donors])
        self.assertItemsEqual([k.winner.id for k in self.prize_keys if k.winner], old_ids + [d.id for d in new_donors])
        all_donors = old_donors + new_donors
        for key in self.prize_keys:
            self.assertIn(key.winner, all_donors, u'%s was not in donors.' % key.winner)
            self.assertEqual(key.prize_winner.pendingcount, 0)
            self.assertEqual(key.prize_winner.acceptcount, 1)
            self.assertEqual(key.prize_winner.declinecount, 0)
            self.assertTrue(key.prize_winner.emailsent)
            self.assertEqual(key.prize_winner.acceptemailsentcount, 1)
            self.assertEqual(key.prize_winner.shippingstate, 'SHIPPED')
            self.assertFalse(key.prize_winner.shippingemailsent)

    def test_more_donors_than_keys(self):
        self.prize.save()
        donors = models.Donor.objects.bulk_create([randgen.generate_donor(self.rand) for _ in range(self.prize_keys.count() * 2)])
        models.Donation.objects.bulk_create(
            [randgen.generate_donation_for_prize(self.rand, donor=d, prize=self.prize) for d in donors]
        )
        self.assertItemsEqual([d['donor'] for d in self.prize.eligible_donors()], [d.id for d in donors])
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertEqual(self.prize.prizewinner_set.count(), self.prize_keys.count())
        for key in self.prize_keys:
            self.assertIn(key.winner, donors, u'%s was not in eligible donors.' % key.winner)
            self.assertIn(key.winner.id, result['winners'], u'%s was not in winners.' % key.winner)
            self.assertEqual(key.prize_winner.pendingcount, 0)
            self.assertEqual(key.prize_winner.acceptcount, 1)
            self.assertEqual(key.prize_winner.declinecount, 0)
            self.assertTrue(key.prize_winner.emailsent)
            self.assertEqual(key.prize_winner.acceptemailsentcount, 1)
            self.assertEqual(key.prize_winner.shippingstate, 'SHIPPED')
            self.assertFalse(key.prize_winner.shippingemailsent)
        old_winners = sorted(result['winners'])
        old_donors = sorted(w.winner.id for w in self.prize.prizewinner_set.all())

        self.prize.prizekey_set.update(prize_winner=None)
        self.prize.prizewinner_set.all().delete()

        # assert actual randomness
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertNotEqual(sorted(result['winners']), old_winners)
        self.assertNotEqual(sorted(w.winner.id for w in self.prize.prizewinner_set.all()), old_donors)


class TestPrizeAdmin(TestCase):
    def assertMessages(self, response, messages):  # TODO: util?
        self.assertItemsEqual([unicode(m) for m in response.wsgi_request._messages], messages)

    def setUp(self):
        self.staff_user = User.objects.create_user(
            'staff', 'staff@example.com', 'staff')
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password')
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event)
        self.prize.save()
        self.prize_with_keys = randgen.generate_prize(self.rand, event=self.event)
        self.prize_with_keys.key_code = True
        self.prize_with_keys.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.prize_winner = models.PrizeWinner.objects.create(
            winner=self.donor, prize=self.prize)
        self.donor_prize_entry = models.DonorPrizeEntry.objects.create(
            donor=self.donor, prize=self.prize)
        self.prize_key = models.PrizeKey.objects.create(prize=self.prize_with_keys, key='dead-beef-dead-beef')

    def test_prize_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prize_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prize_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prize_change', args=(self.prize.id,)))
        self.assertEqual(response.status_code, 200)

    def test_prize_key_import_action(self):
        self.client.login(username='admin', password='password')

        response = self.client.post(reverse('admin:tracker_prize_changelist'),
                                    {'action': 'import_keys_action',
                                     ACTION_CHECKBOX_NAME: [self.prize.id, self.prize_with_keys.id]})
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(reverse('admin:tracker_prize_changelist'),
                                    {'action': 'import_keys_action',
                                     ACTION_CHECKBOX_NAME: [self.prize.id]})
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(reverse('admin:tracker_prize_changelist'),
                                    {'action': 'import_keys_action',
                                     ACTION_CHECKBOX_NAME: [self.prize_with_keys.id]})
        self.assertRedirects(response, reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)))

    def test_prize_key_import_form(self):
        keys = ['dead-beef-dead-beef-123%d' % i for i in range(5)]
        response = self.client.get(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password')
        response = self.client.get(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prize_key_import', args=(self.prize.id,)))
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Cannot import prize keys to non key prizes.'])

        response = self.client.get(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id + 1,)))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)))
        self.assertEqual(response.status_code, 200)

        keys_input = '\n' + ' \n '.join(keys) + '\n%s\n\n' % keys[0]  # test whitespace stripping and deduping
        response = self.client.post(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
                                    {'keys': keys_input})

        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['5 key(s) added to prize.'])
        self.prize_with_keys.refresh_from_db()
        self.assertEqual(self.prize_with_keys.maxwinners, 6)
        self.assertEqual(self.prize_with_keys.prizekey_set.count(), 6)
        self.assertItemsEqual(keys, [key.key for key in self.prize_with_keys.prizekey_set.all()[1:]])

        response = self.client.post(reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
                                    {'keys': keys[0]})
        self.assertFormError(response, 'form', 'keys', ['At least one key already exists.'])

    def test_prize_winner_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse('admin:tracker_prizewinner_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prizewinner_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizewinner_change', args=(self.prize_winner.id,)))
        self.assertEqual(response.status_code, 200)

    def test_donor_prize_entry_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse('admin:tracker_donorprizeentry_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_donorprizeentry_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse(
            'admin:tracker_donorprizeentry_change', args=(self.donor_prize_entry.id,)))
        self.assertEqual(response.status_code, 200)

    def test_prize_key_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prizekey_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prizekey_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizekey_change', args=(self.prize_key.id,)))
        self.assertEqual(response.status_code, 200)
