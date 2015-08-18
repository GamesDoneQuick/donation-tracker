from django.test import TestCase
from django.db.models import ProtectedError
import tracker.randgen as randgen
from dateutil.parser import parse as parse_date
import random
import pytz
import tracker.models
import datetime
import tracker.viewutil as viewutil
from decimal import Decimal
import tracker.filters as filters
import post_office.models
from collections import Counter
import tracker.prizemail as prizemail
import tracker.forms

from django.core.exceptions import ValidationError

class TestDonorTotals(TestCase):
  def setUp(self):
    self.john = tracker.models.Donor.objects.create(firstname='John', lastname='Doe', email='johndoe@example.com')
    self.jane = tracker.models.Donor.objects.create(firstname='Jane', lastname='Doe', email='janedoe@example.com')
    self.ev1 = tracker.models.Event.objects.create(short='ev1',name='Event 1',targetamount=5,date=datetime.date.today())
    self.ev2 = tracker.models.Event.objects.create(short='ev2',name='Event 2',targetamount=5,date=datetime.date.today())
  def test_donor_cache(self):
    self.assertEqual(0, tracker.models.DonorCache.objects.count())
    d1 = tracker.models.Donation.objects.create(donor=self.john,event=self.ev1,amount=5,domainId='d1',transactionstate='COMPLETED',timereceived=datetime.datetime.now(pytz.utc))
    self.assertEqual(2, tracker.models.DonorCache.objects.count())
    d2 = tracker.models.Donation.objects.create(donor=self.john,event=self.ev2,amount=5,domainId='d2',transactionstate='COMPLETED',timereceived=datetime.datetime.now(pytz.utc))
    self.assertEqual(3, tracker.models.DonorCache.objects.count())
    d3 = tracker.models.Donation.objects.create(donor=self.john,event=self.ev2,amount=10,domainId='d3',transactionstate='COMPLETED',timereceived=datetime.datetime.now(pytz.utc))
    self.assertEqual(3, tracker.models.DonorCache.objects.count())
    d4 = tracker.models.Donation.objects.create(donor=self.jane,event=self.ev1,amount=20,domainId='d4',transactionstate='COMPLETED',timereceived=datetime.datetime.now(pytz.utc))
    self.assertEqual(5, tracker.models.DonorCache.objects.count())
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_count)
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_max)
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_avg)
    self.assertEqual(15, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_total)
    self.assertEqual(2, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_count)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_max)
    self.assertEqual(7.5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_avg)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_total)
    self.assertEqual(3, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_count)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_max)
    self.assertAlmostEqual(Decimal(20/3.0), tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_avg, 2)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=self.ev1).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.jane,event=self.ev1).donation_count)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=self.ev1).donation_max)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=self.ev1).donation_avg)
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.jane,event=self.ev2).exists())
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=None).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.jane,event=None).donation_count)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=None).donation_max)
    self.assertEqual(20, tracker.models.DonorCache.objects.get(donor=self.jane,event=None).donation_avg)
    # now change them all to pending to make sure the delete logic for that works
    d2.transactionstate = 'PENDING'
    d2.save()
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_count)
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_max)
    self.assertEqual(5, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev1).donation_avg)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_count)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_max)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=self.ev2).donation_avg)
    self.assertEqual(15, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_total)
    self.assertEqual(2, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_count)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_max)
    self.assertAlmostEqual(Decimal(15/2.0), tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_avg, 2)
    d1.transactionstate = 'PENDING'
    d1.save()
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.john,event=self.ev1).exists())
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_total)
    self.assertEqual(1, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_count)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_max)
    self.assertEqual(10, tracker.models.DonorCache.objects.get(donor=self.john,event=None).donation_avg)
    d3.transactionstate = 'PENDING'
    d3.save()
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.john,event=self.ev2).exists())
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.john,event=None).exists())
    self.assertEqual(2, tracker.models.DonorCache.objects.count()) # jane's stuff still exists
    d4.delete() # delete the last of it to make sure it's all gone
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.jane,event=self.ev1).exists())
    self.assertFalse(tracker.models.DonorCache.objects.filter(donor=self.jane,event=None).exists())
    self.assertEqual(0, tracker.models.DonorCache.objects.count())

class TestPrizeGameRange(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2014-01-01 16:00:00").replace(tzinfo=pytz.utc)
    self.rand = random.Random(None)
    self.event = randgen.generate_event(self.rand, self.eventStart)
    self.event.save()
    self.runs, self.eventEnd = randgen.generate_runs(self.rand, self.event, 50, self.eventStart)
    return
  def test_prize_range_single(self):
    run = self.runs[18]
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=run, endRun=run)
    prizeRuns = prize.games_range()
    self.assertEqual(1, prizeRuns.count())
    self.assertEqual(run.id, prizeRuns[0].id)
    return
  def test_prize_range_pair(self):
    startRun = self.runs[44]
    endRun = self.runs[45]
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=startRun, endRun=endRun)
    prizeRuns = prize.games_range()
    self.assertEqual(2, prizeRuns.count())
    self.assertEqual(startRun.id, prizeRuns[0].id)
    self.assertEqual(endRun.id, prizeRuns[1].id)
    return
  def test_prize_range_gap(self):
    runsSlice = self.runs[24:34]
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=runsSlice[0], endRun=runsSlice[-1])
    prizeRuns = prize.games_range()
    self.assertEqual(len(runsSlice), prizeRuns.count())
    for i in range(0, len(runsSlice)):
      self.assertEqual(runsSlice[i].id, prizeRuns[i].id)
    return
  def test_time_prize_no_range(self):
    timeA = randgen.random_time(self.rand, self.eventStart, self.eventEnd)
    timeB = randgen.random_time(self.rand, self.eventStart, self.eventEnd)
    randomStart = min(timeA, timeB)
    randomEnd = max(timeA, timeB)
    prize = randgen.generate_prize(self.rand, event=self.event, startTime=randomStart, endTime=randomEnd)
    prizeRuns = prize.games_range()
    self.assertEqual(0, prizeRuns.count())
    return
  def test_prize_times(self):
    runsSlice = self.runs[6:20]
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=runsSlice[0], endRun=runsSlice[-1])
    self.assertEqual(runsSlice[0].starttime, prize.start_draw_time())
    self.assertEqual(runsSlice[-1].endtime, prize.end_draw_time())
    prize.startrun = None
    prize.endrun = None
    timeA = randgen.random_time(self.rand, self.eventStart, self.eventEnd)
    timeB = randgen.random_time(self.rand, self.eventStart, self.eventEnd)
    prize.starttime = min(timeA, timeB)
    prize.endtime = max(timeA, timeB)
    self.assertEqual(min(timeA, timeB), prize.start_draw_time())
    self.assertEqual(max(timeA, timeB), prize.end_draw_time())
    return

class TestPrizeDrawingGeneratedEvent(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2014-01-01 16:00:00").replace(tzinfo=pytz.utc)
    self.rand = random.Random(516273)
    self.event = randgen.build_random_event(self.rand, self.eventStart, numDonors=100, numRuns=50)
    self.runsList = list(tracker.models.SpeedRun.objects.filter(event=self.event))
    self.donorList = list(tracker.models.Donor.objects.all())
    return
  def test_draw_random_prize_no_donations(self):
    prizeList = randgen.generate_prizes(self.rand, self.event, 50, self.runsList)
    for prize in prizeList:
      for randomness in [True, False]:
        for useSum in [True, False]:
          prize.randomdraw = randomness
          prize.sumdonations = useSum
          prize.save()
          eligibleDonors = prize.eligible_donors()
          self.assertEqual(0, len(eligibleDonors))
          result, message = viewutil.draw_prize(prize)
          self.assertFalse(result)
          self.assertEqual(0, len(prize.get_winners()))
    return
  def test_draw_prize_one_donor(self):
    startRun = self.runsList[14]
    endRun = self.runsList[28]
    for useRandom in [True, False]:
      for useSum in [True, False]:
        for donationSize in ['top', 'bottom', 'above', 'below', 'within']:
          prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=useSum, randomDraw=useRandom, startRun=startRun, endRun=endRun)
          prize.save()
          donor = randgen.pick_random_element(self.rand, self.donorList)
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
          if donationSize == 'above':
            donation.amount = prize.maximumbid + Decimal('5.00')
          elif donationSize == 'top':
            donation.amount = prize.maximumbid
          elif donationSize == 'within':
            donation.amount = randgen.random_amount(self.rand, rounded=False, minAmount=prize.minimumbid, maxAmount=prize.maximumbid)
          elif donationSize == 'bottom':
            donation.amount = prize.minimumbid
          elif donationSize == 'below':
            donation.amount = max(Decimal('0.00'), prize.minimumbid - Decimal('5.00'))
          donation.save()
          eligibleDonors = prize.eligible_donors()
          if donationSize == 'below' and prize.randomdraw:
            self.assertEqual(0, len(eligibleDonors))
          else:
            self.assertEqual(1, len(eligibleDonors))
            self.assertEqual(donor.id, eligibleDonors[0]['donor'])
            self.assertEqual(donation.amount, eligibleDonors[0]['amount'])
            if prize.sumdonations and prize.randomdraw:
              if donationSize == 'top' or donationSize == 'above':
                expectedRatio = float(prize.maximumbid / prize.minimumbid)
              else:
                expectedRatio = float(donation.amount / prize.minimumbid)
              self.assertAlmostEqual(expectedRatio, eligibleDonors[0]['weight'])
            else:
              self.assertEqual(1.0, eligibleDonors[0]['weight'])
          result, message = viewutil.draw_prize(prize)
          if donationSize != 'below' or not prize.randomdraw:
            self.assertTrue(result)
            self.assertEqual(donor, prize.get_winner())
          else:
            self.assertFalse(result)
            self.assertEqual(None, prize.get_winner())
          donation.delete()
          prize.prizewinner_set.all().delete()
          prize.delete()
    return
  def test_draw_prize_multiple_donors_random_nosum(self):
    startRun = self.runsList[28]
    endRun = self.runsList[30]
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=False, randomDraw=True, startRun=startRun, endRun=endRun)
    prize.save()
    donationDonors = {}
    for donor in self.donorList:
      if self.rand.getrandbits(1) == 0:
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        donationDonors[donor.id] = donor
      # Add a few red herrings to make sure out of range donations aren't used
      donation2 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
      donation2.save()
      donation3 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
      donation3.save()
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(len(donationDonors.keys()), len(eligibleDonors))
    for eligibleDonor in eligibleDonors:
      found = False
      if eligibleDonor['donor'] in donationDonors:
        donor = donationDonors[eligibleDonor['donor']]
        donation = donor.donation_set.filter(timereceived__gte=prize.start_draw_time(), timereceived__lte=prize.end_draw_time())[0]
        self.assertEqual(donation.amount, eligibleDonor['amount'])
        self.assertEqual(1.0, eligibleDonor['weight'])
        found = True
      self.assertTrue(found and "Could not find the donor in the list")
    winners = []
    for seed in [15634, 12512, 666]:
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertIn(prize.get_winner().id, donationDonors)
      winners.append(prize.get_winner())
      current = prize.get_winner()
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(current, prize.get_winner())
      prize.prizewinner_set.all().delete()
      prize.save()
    self.assertNotEqual(winners[0], winners[1])
    self.assertNotEqual(winners[1], winners[2])
    self.assertNotEqual(winners[0], winners[2])
    return
  def test_draw_prize_multiple_donors_random_sum(self):
    startRun = self.runsList[41]
    endRun = self.runsList[46]
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, startRun=startRun, endRun=endRun)
    prize.save()
    donationDonors = {}
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4)
      redHerrings = self.rand.getrandbits(4)
      donationDonors[donor.id] = { 'donor': donor, 'amount': Decimal('0.00') }
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        donationDonors[donor.id]['amount'] += donation.amount
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
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
          donations = donor.donation_set.filter(timereceived__gte=prize.start_draw_time(), timereceived__lte=prize.end_draw_time())
          countAmount = Decimal('0.00')
          for donation in donations:
            countAmount += donation.amount
          self.assertEqual(entry['amount'], eligibleDonor['amount'])
          self.assertEqual(countAmount, eligibleDonor['amount'])
          self.assertAlmostEqual(min(prize.maximumbid / prize.minimumbid, entry['amount'] / prize.minimumbid), Decimal(eligibleDonor['weight']))
          found = True
    self.assertTrue(found and "Could not find the donor in the list")
    winners = []
    for seed in [51234, 235426, 62363245]:
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertIn(prize.get_winner().id, donationDonors)
      winners.append(prize.get_winner())
      current = prize.get_winner()
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(current, prize.get_winner())
      prize.prizewinner_set.all().delete()
      prize.save()
    self.assertNotEqual(winners[0], winners[1])
    self.assertNotEqual(winners[1], winners[2])
    self.assertNotEqual(winners[0], winners[2])
    return
  def test_draw_prize_multiple_donors_norandom_nosum(self):
    startRun = self.runsList[25]
    endRun = self.runsList[34]
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=False, randomDraw=False, startRun=startRun, endRun=endRun)
    prize.save()
    largestDonor = None
    largestAmount = Decimal('0.00')
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4)
      redHerrings = self.rand.getrandbits(4)
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=Decimal('1000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        if donation.amount > largestAmount:
          largestDonor = donor
          largestAmount = donation.amount
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
        donation.save()
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(largestDonor.id, eligibleDonors[0]['donor'])
    self.assertEqual(1.0, eligibleDonors[0]['weight'])
    self.assertEqual(largestAmount, eligibleDonors[0]['amount'])
    for seed in [9524,373, 747]:
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(largestDonor.id, prize.get_winner().id)
    newDonor = randgen.generate_donor(self.rand)
    newDonor.save()
    newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
    newDonation.save()
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(newDonor.id, eligibleDonors[0]['donor'])
    self.assertEqual(1.0, eligibleDonors[0]['weight'])
    self.assertEqual(newDonation.amount, eligibleDonors[0]['amount'])
    for seed in [9524,373, 747]:
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(newDonor.id, prize.get_winner().id)
  def test_draw_prize_multiple_donors_norandom_sum(self):
    startRun = self.runsList[5]
    endRun = self.runsList[9]
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=False, startRun=startRun, endRun=endRun)
    prize.save()
    donationDonors = {}
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4)
      redHerrings = self.rand.getrandbits(4)
      donationDonors[donor.id] = { 'donor': donor, 'amount': Decimal('0.00') }
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        donationDonors[donor.id]['amount'] += donation.amount
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1))
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1))
        donation.save()
    maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1]
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor'])
    self.assertEqual(1.0, eligibleDonors[0]['weight'])
    self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount'])
    for seed in [9524,373, 747]:
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(maxDonor['donor'].id, prize.get_winner().id)
    oldMaxDonor = maxDonor
    del donationDonors[oldMaxDonor['donor'].id]
    maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1]
    diff = oldMaxDonor['amount'] - maxDonor['amount']
    newDonor = maxDonor['donor']
    newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=diff + Decimal('0.01'), maxAmount=diff + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
    newDonation.save()
    maxDonor['amount'] += newDonation.amount
    prize = tracker.models.Prize.objects.get(id=prize.id)
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor'])
    self.assertEqual(1.0, eligibleDonors[0]['weight'])
    self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount'])
    for seed in [9524,373, 747]:
      prize.prizewinner_set.all().delete()
      prize.save()
      result, message = viewutil.draw_prize(prize, seed)
      self.assertTrue(result)
      self.assertEqual(maxDonor['donor'].id, prize.get_winner().id)

class TestTicketPrizeDraws(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2012-01-01 01:00:00").replace(tzinfo=pytz.utc)
    self.rand = random.Random(998164)
    self.event = randgen.build_random_event(self.rand, self.eventStart, numDonors=100, numRuns=50)
    self.runsList = list(tracker.models.SpeedRun.objects.filter(event=self.event))
    self.donorList = list(tracker.models.Donor.objects.all())
  def test_draw_prize_with_tickets_no_donations(self):
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
    prize.save()
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(0, len(eligibleDonors))
    result, message = viewutil.draw_prize(prize)
    self.assertFalse(result)
    self.assertEqual(None, prize.get_winner())
  def test_draw_prize_with_tickets(self):
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
    prize.maximumbid = None
    prize.save()
    donor = self.donorList[0]
    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
    donation.save()
    tracker.models.PrizeTicket.objects.create(donation=donation, prize=prize, amount=donation.amount)
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(eligibleDonors[0]['donor'], donor.id)
    result, message = viewutil.draw_prize(prize)
    self.assertTrue(result)
    self.assertEqual(donor, prize.get_winner())
  def test_draw_prize_with_tickets_multiple_donors(self):
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
    prize.maximumbid = None
    prize.save()
    donor = self.donorList[0]
    donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
    donation.save()
    tracker.models.PrizeTicket.objects.create(donation=donation, prize=prize, amount=donation.amount)
    donor2 = self.donorList[1]
    donation2 = randgen.generate_donation(self.rand, donor=donor2, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
    donation2.save()
    eligibleDonors = prize.eligible_donors()
    self.assertEqual(1, len(eligibleDonors))
    self.assertEqual(eligibleDonors[0]['donor'], donor.id)
    self.assertAlmostEqual(eligibleDonors[0]['weight'], donation.amount / prize.minimumbid)
    result, message = viewutil.draw_prize(prize)
    self.assertTrue(result)
    self.assertEqual(donor, prize.get_winner())
  def test_correct_prize_amount_with_split_tickets(self):
    prize0 = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True) 
    prize0.maximumbid = None
    prize0.save()
    prize1 = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
    prize1.maximumbid = None
    prize1.save()
    donor = self.donorList[0]
    donation = randgen.generate_donation(self.rand, donor=donor,event=self.event, minAmount=prize0.minimumbid+prize1.minimumbid)
    donation.save()
    prize0Eligible = prize0.eligible_donors()
    self.assertEqual(0, len(prize0Eligible))
    prize1Eligible = prize1.eligible_donors()
    self.assertEqual(0, len(prize1Eligible))
    tracker.models.PrizeTicket.objects.create(donation=donation, prize=prize0, amount=donation.amount*Decimal('2.0')) 
    tracker.models.PrizeTicket.objects.create(donation=donation, prize=prize1, amount=donation.amount*Decimal('2.0'))
    prize0Eligible = prize0.eligible_donors()
    self.assertEqual(1, len(prize0Eligible))
    prize1Eligible = prize1.eligible_donors()
    self.assertEqual(1, len(prize1Eligible))
    # TODO: more of these tests

class TestDonorPrizeEntryDraw(TestCase):
  def setUp(self):
    self.rand = random.Random(9239234)
    self.event = randgen.generate_event(self.rand)
    self.event.save()
  def testSingleEntry(self):
    donor = randgen.generate_donor(self.rand)
    donor.save()
    prize = randgen.generate_prize(self.rand,event=self.event)
    prize.save()
    entry = tracker.models.DonorPrizeEntry(donor=donor,prize=prize)
    entry.save()
    eligible = prize.eligible_donors()
    self.assertEqual(1, len(eligible))
    self.assertEqual(donor.pk, eligible[0]['donor'])
    self.assertEqual(entry.weight, eligible[0]['weight'])
  def testMultipleEntries(self):
    numDonors = 5
    donors = []
    prize = randgen.generate_prize(self.rand,event=self.event)
    prize.save()
    for i in range(0,numDonors):
      donor = randgen.generate_donor(self.rand)
      donor.save()
      entry = tracker.models.DonorPrizeEntry(donor=donor,prize=prize)
      entry.save()
      donors.append(donor.pk)
    eligible = prize.eligible_donors()
    self.assertEqual(numDonors, len(eligible))
    for donorId in map(lambda x: x['donor'], eligible):
      self.assertTrue(donorId in donors) 

class TestMergeSchedule(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2012-01-01 01:00:00")
    self.rand = random.Random(632434)
    self.event = randgen.build_random_event(self.rand, startTime=self.eventStart)
    self.event.scheduledatetimefield = "time"
    self.event.schedulegamefield = "game"
    self.event.schedulerunnersfield = "runners"
    self.event.scheduleestimatefield = "estimate"
    self.event.schedulesetupfield = "setup"
    self.event.schedulecommentatorsfield = "commentators"
    self.event.schedulecommentsfield = "comments"
    self.event.save()

  def test_case_sensitive_runs(self):
    ssRuns = []
    ssRuns.append({"time": "9/5/2014 12:00:00", "game": "CaSe SeNsItIvE", "runners": "A Runner1", "estimate": "1:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
    viewutil.merge_schedule_list(self.event, ssRuns)
    runs = tracker.models.SpeedRun.objects.filter(event=self.event)
    self.assertEqual(1, runs.count())
    self.assertEqual("CaSe SeNsItIvE", runs[0].name)

  def test_delete_missing_runs(self):
    ssRuns = []
    ssRuns.append({"time": "9/5/2014 12:00:00", "game": "Game 1", "runners": "A Runner1", "estimate": "1:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
    ssRuns.append({"time": "9/5/2014 13:00:00", "game": "Game 2", "runners": "A Runner2", "estimate": "1:30:00", "setup": "0:00:00", "commentators": "", "comments": ""})
    ssRuns.append({"time": "9/5/2014 14:30:00", "game": "Game 3", "runners": "A Runner3", "estimate": "2:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
    viewutil.merge_schedule_list(self.event, ssRuns)
    runs = tracker.models.SpeedRun.objects.filter(event=self.event)
    self.assertEqual(3, runs.count())
    ssRuns.pop(1)
    viewutil.merge_schedule_list(self.event, ssRuns)
    runs = tracker.models.SpeedRun.objects.filter(event=self.event)
    self.assertEqual(2, runs.count())
    self.assertEqual("Game 1", runs[0].name)
    self.assertEqual("Game 3", runs[1].name)

def parse_mail(mail):
  lines = list(map(lambda x: x.partition(':'), filter(lambda x: x, map(lambda x: x.strip(), mail.message.split("\n")))))
  result = {}
  for line in lines:
    if line[2]:
      name = line[0].lower()
      value = line[2]
      if name not in result:
        result[name] = []
      result[name].append(value)
  return result

class TestAutomailPrizeContributors(TestCase):
  testTemplateContent = """
  EVENT:{{ event.id }}
  NAME:{{ contributorName }}
  {% for prize in acceptedPrizes %}
    ACCEPTED:{{ prize.id }}
  {% endfor %}
  {% for prize in deniedPrizes %}
    DENIED:{{ prize.id }}
  {% endfor %}
  """
  def setUp(self):
    self.eventStart = parse_date("2014-02-02 05:00:05")
    self.rand = random.Random(839740)
    self.numDonors = 10
    self.numPrizes = 40
    self.event = randgen.build_random_event(self.rand, startTime=self.eventStart, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
    # eventually, this should be a database fixture that is loaded on syncdb, todo: figure out how to load fixtures
    self.templateEmail = post_office.models.EmailTemplate.objects.create(name="testing_prize_submission_response", description="", subject="A Test", content=self.testTemplateContent)

  def _parseMail(self, mail):
    contents = parse_mail(mail)
    event = int(contents['event'][0])
    name = contents['name'][0]
    accepted = list(map(lambda x: int(x), contents.get('accepted', [])))
    denied = list(map(lambda x: int(x), contents.get('denied', [])))
    return event, name, accepted, denied

  def testAutoMail(self):
    donors = tracker.models.Donor.objects.all()
    prizes = tracker.models.Prize.objects.all()
    acceptCount = 0
    denyCount = 0
    pendingCount = 0
    donorPrizes = {}
    for donor in donors:
      donorPrizes[donor.id] = ([],[])
      if donor.id % 2 == 0:
        donor.alias = None
        donor.save()
    for prize in prizes:
      donor = donors[self.rand.randrange(self.numDonors)]
      prize.provided = donor.alias
      prize.provideremail = donor.email
      pickVal = self.rand.randrange(3)
      if pickVal == 0:
        prize.state = "ACCEPTED"
        acceptCount += 1
        donorPrizes[donor.id][0].append(prize)
      elif pickVal == 1:
        prize.state = "DENIED"
        denyCount += 1
        donorPrizes[donor.id][1].append(prize)
      else:
        prize.state = "PENDING"
        pendingCount += 1
      prize.save()
    processedPrizes = prizemail.prizes_with_submission_email_pending(self.event)
    self.assertEqual(acceptCount + denyCount, processedPrizes.count())
    prizemail.automail_prize_contributors(self.event, processedPrizes, self.templateEmail, sender='nobody@nowhere.com')
    prizes = tracker.models.Prize.objects.all()
    for prize in prizes:
      if prize.state == "PENDING":
        self.assertFalse(prize.acceptemailsent)
      else:
        self.assertTrue(prize.acceptemailsent)
    for donor in donors:
      acceptedPrizes, deniedPrizes = donorPrizes[donor.id]
      donorMail = post_office.models.Email.objects.filter(to=donor.email)
      if len(acceptedPrizes) == 0 and len(deniedPrizes) == 0:
        self.assertEqual(0, donorMail.count())
      else:
        self.assertEqual(1, donorMail.count())
        eventId, name, acceptedIds, deniedIds = self._parseMail(donorMail[0])
        self.assertEqual(self.event.id, eventId)
        if donor.alias == None:
          self.assertEqual(donor.email, name)
        else:
          self.assertEqual(donor.alias, name)
        self.assertEqual(len(acceptedPrizes), len(acceptedIds))
        self.assertEqual(len(deniedPrizes), len(deniedIds))
        for prize in acceptedPrizes:
          self.assertTrue(prize.id in acceptedIds)
        for prize in deniedPrizes:
          self.assertTrue(prize.id in deniedIds)

class TestDeleteProtection(TestCase):
  def setUp(self):
    self.event = tracker.models.Event.objects.create(short='scratch', name='Scratch Event', date=datetime.date(2000, 1, 1), targetamount=1000)

  def tearDown(self):
    for m in [tracker.models.PrizeWinner, tracker.models.PrizeTicket, tracker.models.DonationBid, tracker.models.Bid,
              tracker.models.Donation, tracker.models.Prize, tracker.models.Donor, tracker.models.SpeedRun]:
      m.objects.all().delete()

  def assertDeleteProtected(self, deleted, protected):
    protected.clean()
    with self.assertRaises(ProtectedError):
      deleted.delete()
    protected.delete()

  class Delete:
    def __init__(self, obj):
      self.obj = obj
      assert hasattr(self.obj, 'clean')
      assert hasattr(self.obj, 'delete')

    def __enter__(self):
      self.obj.clean()
      return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
      self.obj.delete()

  @property
  def scratchPrizeTimed(self):
    return tracker.models.Prize.objects.get_or_create(name='Scratch Prize Timed', event=self.event,
                                                      defaults=dict(
                                                        starttime=datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                                                        endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc)))[0]

  @property
  def scratchPrizeTicketed(self):
    return tracker.models.Prize.objects.get_or_create(name='Scratch Prize Ticketed', event=self.event,
                                                      defaults=dict(ticketdraw=True))[0]

  @property
  def scratchPrizeRun(self):
    return tracker.models.Prize.objects.get_or_create(name='Scratch Prize Run', event=self.event,
                                                      defaults=dict(
                                                        startrun=self.scratchRun, endrun=self.scratchRun))[0]

  @property
  def scratchPrizeWinner(self):
    return tracker.models.PrizeWinner.objects.get_or_create(winner=self.scratchDonor, prize=self.scratchPrizeTimed)[0]

  @property
  def scratchPrizeWinnerTicketed(self):
    return tracker.models.PrizeWinner.objects.get_or_create(winner=self.scratchDonor, prize=self.scratchPrizeTicketed)[0]

  @property
  def scratchPrizeTicket(self):
    return tracker.models.PrizeTicket.objects.get_or_create(prize=self.scratchPrizeTicketed, donation=self.scratchDonation,
                                                            defaults=dict(amount=5))[0]

  @property
  def scratchDonor(self):
    return tracker.models.Donor.objects.get_or_create(email='scratch_donor@example.com')[0]

  @property
  def scratchDonation(self):
    return tracker.models.Donation.objects.get_or_create(domainId='scratch',
                                                         defaults=dict(
                                                           domain='PAYPAL', event=self.event, amount=5))[0]

  @property
  def scratchDonationWithDonor(self):
    return tracker.models.Donation.objects.get_or_create(domainId='scratchDonor',
                                                         defaults=dict(
                                                           domain='PAYPAL', event=self.event, donor=self.scratchDonor,
                                                           amount=5, transactionstate='COMPLETED'))[0]

  @property
  def scratchDonationBid(self):
    return tracker.models.DonationBid.objects.get_or_create(donation=self.scratchDonation, bid=self.scratchBidRun, amount=5)[0]

  @property
  def scratchRun(self):
    return tracker.models.SpeedRun.objects.get_or_create(name='Scratch Run', event=self.event,
                                                         defaults=dict(
                                                           starttime=datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                                                           endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc)))[0]

  @property
  def scratchBidEvent(self):
    return tracker.models.Bid.objects.get_or_create(name='Scratch Bid', event=self.event)[0]

  @property
  def scratchBidRun(self):
    return tracker.models.Bid.objects.get_or_create(name='Scratch Bid', speedrun=self.scratchRun)[0]

  def testDeleteEvent(self):
    self.assertDeleteProtected(self.event, self.scratchBidEvent)
    self.assertDeleteProtected(self.event, self.scratchRun)
    self.assertDeleteProtected(self.event, self.scratchPrizeTimed)
    self.assertDeleteProtected(self.event, self.scratchDonation)
    with self.Delete(tracker.models.Event.objects.create(short='delete', name='Delete Event',
                                                         date=datetime.date(2001, 1, 1), targetamount=1000)):
      pass

  def testDeleteRun(self):
    with self.Delete(self.scratchRun) as run:
      self.assertDeleteProtected(run, self.scratchPrizeRun)
      self.assertDeleteProtected(run, self.scratchBidRun)

  def testDeletePrize(self):
    with self.Delete(self.scratchPrizeTicketed) as prize:
      self.assertDeleteProtected(prize, self.scratchPrizeWinnerTicketed)
      self.assertDeleteProtected(prize, self.scratchPrizeTicket)

  def testDeleteDonor(self):
    with self.Delete(self.scratchDonor) as donor:
      self.assertDeleteProtected(donor, self.scratchPrizeWinner)
      self.assertDeleteProtected(donor, self.scratchDonationWithDonor)

  def testDeleteDonation(self):
    with self.Delete(self.scratchDonation) as donation:
      self.assertDeleteProtected(donation, self.scratchDonationBid)
      self.assertDeleteProtected(donation, self.scratchPrizeTicket)

class TestAutomailPrizeWinners(TestCase):
  emailTemplate = """
  EVENT:{{ event.id }}
  WINNER:{{ winner.id }}
  {% for prize in prizes %}
    PRIZE: {{ prize.id }}
  {% endfor %}
  """

  def setUp(self):
    self.eventStart = parse_date("2014-02-02 05:00:05")
    self.rand = random.Random(8556142)
    self.numDonors = 60
    self.numPrizes = 400
    self.event = randgen.build_random_event(self.rand, startTime=self.eventStart, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
    self.templateEmail = post_office.models.EmailTemplate.objects.create(name="testing_prize_winner_notification", description="", subject="You Win!", content=self.emailTemplate)

  def _parseMail(self, mail):
    contents = parse_mail(mail)
    event = int(contents['event'][0])
    winner = int(contents['winner'][0])
    prizes = list(map(lambda x: int(x), contents.get('prize', [])))
    return event, winner, prizes

  def testAutoMail(self):
    donors = list(tracker.models.Donor.objects.all())
    prizes = list(tracker.models.Prize.objects.all())
    fullWinnerList = []
    donorWins = {}
    for prize in prizes:
      if self.rand.getrandbits(1) == 0:
        winners = []
        while len(winners) < prize.maxwinners:
          d = donors[self.rand.randrange(len(donors))]
          if d not in winners:
            winners.append(d)
        for winner in winners:
          fullWinnerList.append(tracker.models.PrizeWinner.objects.create(winner=winner, prize=prize))
          donorPrizeList = donorWins.get(winner.id, None)
          if donorPrizeList == None:
            donorPrizeList = []
            donorWins[winner.id] = donorPrizeList
          donorPrizeList.append(prize)
    prizemail.automail_prize_winners(self.event, fullWinnerList, self.templateEmail, sender='nobody@nowhere.com')
    prizeWinners = tracker.models.PrizeWinner.objects.all()
    self.assertEqual(len(fullWinnerList), prizeWinners.count())
    for prizeWinner in prizeWinners:
      self.assertTrue(prizeWinner.emailsent)
    for donor in donors:
      wonPrizes = donorWins.get(donor.id, [])
      donorMail = post_office.models.Email.objects.filter(to=donor.email)
      if len(wonPrizes) == 0:
        self.assertEqual(0, donorMail.count())
      else:
        self.assertEqual(1, donorMail.count())
        eventId, winnerId, prizeIds = self._parseMail(donorMail[0])
        self.assertEqual(self.event.id, eventId)
        self.assertEqual(donor.id, winnerId)
        self.assertEqual(len(wonPrizes), len(prizeIds))
        for prize in wonPrizes:
          self.assertTrue(prize.id in prizeIds)

class TestPersistentPrizeWinners(TestCase):
  def setUp(self):
    self.rand = random.Random(None)
    self.event = randgen.generate_event(self.rand)
    self.event.save()
  # checks that a prize with a single eligible winner keeps track of a declined prize, and disallows that person from being drawn again
  def test_decline_prize_single(self):
    amount = Decimal('50.0')
    targetPrize = randgen.generate_prize(self.rand,event=self.event,sumDonations=False,randomDraw=False,minAmount=amount,maxAmount=amount,maxwinners=1)
    targetPrize.save()
    self.assertEqual(0, len(targetPrize.eligible_donors()))
    donorA = randgen.generate_donor(self.rand)
    donorA.save()
    donorB = randgen.generate_donor(self.rand)
    donorB.save()
    donationA = randgen.generate_donation(self.rand,donor=donorA,minAmount=amount,maxAmount=amount,event=self.event)
    donationA.save()
    self.assertEqual(1, len(targetPrize.eligible_donors()))
    self.assertEqual(donorA.id, targetPrize.eligible_donors()[0]['donor'])
    viewutil.draw_prize(targetPrize)
    self.assertEqual(donorA, targetPrize.get_winner())
    self.assertEqual(0, len(targetPrize.eligible_donors()))
    donationB = randgen.generate_donation(self.rand,donor=donorB,minAmount=amount,maxAmount=amount,event=self.event)
    donationB.save()
    self.assertEqual(1, len(targetPrize.eligible_donors()))
    self.assertEqual(donorB.id, targetPrize.eligible_donors()[0]['donor'])
    prizeWinnerEntry = targetPrize.prizewinner_set.filter(winner=donorA)[0]
    prizeWinnerEntry.acceptstate = 'DECLINED';
    prizeWinnerEntry.save()
    self.assertEqual(1, len(targetPrize.eligible_donors()))
    self.assertEqual(donorB.id, targetPrize.eligible_donors()[0]['donor'])
    viewutil.draw_prize(targetPrize)
    self.assertEqual(donorB, targetPrize.get_winner())
    self.assertEqual(1, len(targetPrize.get_winners()))
    self.assertEqual(0, len(targetPrize.eligible_donors()))
  def test_cannot_exceed_max_winners(self):
    targetPrize = randgen.generate_prize(self.rand,event=self.event)
    targetPrize.maxwinners=2
    targetPrize.save()
    numDonors = 4
    donors = []
    for i in range(0, numDonors):
      donor = randgen.generate_donor(self.rand)
      donor.save()
      donors.append(donor)
    pw0 = tracker.models.PrizeWinner(winner=donors[0], prize=targetPrize)
    pw0.clean()
    pw0.save()
    pw1 = tracker.models.PrizeWinner(winner=donors[1], prize=targetPrize)
    pw1.clean()
    pw1.save()
    with self.assertRaises(ValidationError):
      pw2 = tracker.models.PrizeWinner(winner=donors[2], prize=targetPrize) 
      pw2.clean()
    pw0.acceptstate = 'DECLINED'
    pw0.save()
    pw2.clean()
    pw2.save()

class TestDonorEmailSave(TestCase):
  def testSaveWithExistingDoesNotThrow(self):
    rand = random.Random(None)
    d1 = randgen.generate_donor(rand)
    d1.paypalemail = d1.email
    d1.clean()
    d1.save()
    d1.clean()

class TestDonorNameAssignment(TestCase):
  def testAliasAnonToVisibilityAnon(self):
    data = {
      'amount': Decimal('5.00'),
      'requestedvisibility': 'ALIAS',
      'requestedalias': 'Anonymous', }
    form = tracker.forms.DonationEntryForm(data=data)
    self.assertTrue(form.is_valid())
    self.assertEqual(form.cleaned_data['requestedvisibility'], 'ANON')
    self.assertFalse(bool(form.cleaned_data['requestedalias']))

class TestDonorMerge(TestCase):
  def testBasicMerge(self):
    rand = random.Random(None)
    ev = randgen.build_random_event(rand, numDonors=10, numDonations=20, numRuns=10)
    donorList = tracker.models.Donor.objects.all()
    rootDonor = donorList[0]
    donationList = []
    for donor in donorList:
      donationList.extend(list(donor.donation_set.all()))
    result = viewutil.merge_donors(rootDonor, donorList)
    for donor in donorList[1:]:
      self.assertFalse(tracker.models.Donor.objects.filter(id=donor.id).exists())
    self.assertEquals(len(donationList), rootDonor.donation_set.count()) 
    for donation in rootDonor.donation_set.all():
      self.assertTrue(donation in donationList)
  
