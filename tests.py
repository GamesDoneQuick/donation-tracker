"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
import tracker.randgen as randgen;
from dateutil.parser import parse as parse_date;
import random;
import pytz;
import tracker.models;
import datetime;
import tracker.viewutil as viewutil;
from decimal import Decimal;

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

class TestPrizeGameRange(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2014-01-01 16:00:00").replace(tzinfo=pytz.utc);
    self.rand = random.Random(None);
    self.event = randgen.generate_event(self.rand, self.eventStart);
    self.event.save();
    self.runs, self.eventEnd = randgen.generate_runs(self.rand, self.event, 50, self.eventStart);
    return;
  def test_prize_range_single(self):
    run = self.runs[18];
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=run, endRun=run);
    prizeRuns = prize.games_range();
    self.assertEqual(1, prizeRuns.count());
    self.assertEqual(run.id, prizeRuns[0].id);
    return;
  def test_prize_range_pair(self):
    startRun = self.runs[44];
    endRun = self.runs[45];
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=startRun, endRun=endRun);
    prizeRuns = prize.games_range();
    self.assertEqual(2, prizeRuns.count());
    self.assertEqual(startRun.id, prizeRuns[0].id);
    self.assertEqual(endRun.id, prizeRuns[1].id);
    return;
  def test_prize_range_gap(self):
    runsSlice = self.runs[24:34];
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=runsSlice[0], endRun=runsSlice[-1]);
    prizeRuns = prize.games_range();
    self.assertEqual(len(runsSlice), prizeRuns.count());
    for i in range(0, len(runsSlice)):
      self.assertEqual(runsSlice[i].id, prizeRuns[i].id);
    return;
  def test_time_prize_no_range(self):
    timeA = randgen.random_time(self.rand, self.eventStart, self.eventEnd);
    timeB = randgen.random_time(self.rand, self.eventStart, self.eventEnd);
    randomStart = min(timeA, timeB);
    randomEnd = max(timeA, timeB);
    prize = randgen.generate_prize(self.rand, event=self.event, startTime=randomStart, endTime=randomEnd);
    prizeRuns = prize.games_range();
    self.assertEqual(0, prizeRuns.count());
    return;
  def test_prize_times(self):
    runsSlice = self.runs[6:20];
    prize = randgen.generate_prize(self.rand, event=self.event, startRun=runsSlice[0], endRun=runsSlice[-1]);
    self.assertEqual(runsSlice[0].starttime, prize.start_draw_time());
    self.assertEqual(runsSlice[-1].endtime, prize.end_draw_time());
    prize.startrun = None;
    prize.endrun = None;
    timeA = randgen.random_time(self.rand, self.eventStart, self.eventEnd);
    timeB = randgen.random_time(self.rand, self.eventStart, self.eventEnd);
    prize.starttime = min(timeA, timeB);
    prize.endtime = max(timeA, timeB);
    self.assertEqual(min(timeA, timeB), prize.start_draw_time());
    self.assertEqual(max(timeA, timeB), prize.end_draw_time());
    return;

class TestPrizeDrawingGeneratedEvent(TestCase):
  def setUp(self):
    self.eventStart = parse_date("2014-01-01 16:00:00").replace(tzinfo=pytz.utc);
    self.rand = random.Random(516273);
    self.event = randgen.build_random_event(self.rand, self.eventStart, numDonors=100, numRuns=50);
    self.runsList = list(tracker.models.SpeedRun.objects.filter(event=self.event));
    self.donorList = list(tracker.models.Donor.objects.all());
    return;
  def test_draw_random_prize_no_donations(self):
    prizeList = randgen.generate_prizes(self.rand, self.event, 50, self.runsList);
    for prize in prizeList:
      for randomness in [True, False]:
        for useSum in [True, False]:
          prize.randomdraw = randomness;
          prize.sumdonations = useSum;
          prize.save();
          eligibleDonors = prize.eligible_donors();
          self.assertEqual(0, len(eligibleDonors));
          result, message = viewutil.draw_prize(prize);
          self.assertFalse(result);
          self.assertEqual(None, prize.winner);
    return;
  def test_draw_prize_one_donor(self):
    startRun = self.runsList[14];
    endRun = self.runsList[28];
    for useRandom in [True, False]:
      for useSum in [True, False]:
        for donationSize in ['top', 'bottom', 'above', 'below', 'within']:
          prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=useSum, randomDraw=useRandom, startRun=startRun, endRun=endRun);
          prize.save();
          donor = randgen.pick_random_element(self.rand, self.donorList);
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
          if donationSize == 'above':
            donation.amount = prize.maximumbid + Decimal('5.00');
          elif donationSize == 'top':
            donation.amount = prize.maximumbid;
          elif donationSize == 'within':
            donation.amount = randgen.random_amount(self.rand, rounded=False, minAmount=prize.minimumbid, maxAmount=prize.maximumbid);
          elif donationSize == 'bottom':
            donation.amount = prize.minimumbid;
          elif donationSize == 'below':
            donation.amount = max(Decimal('0.00'), prize.minimumbid - Decimal('5.00'));
          donation.save();
          eligibleDonors = prize.eligible_donors();
          if donationSize == 'below' and prize.randomdraw:
            self.assertEqual(0, len(eligibleDonors));
          else:
            self.assertEqual(1, len(eligibleDonors));
            self.assertEqual(donor.id, eligibleDonors[0]['donor']);
            self.assertEqual(donation.amount, eligibleDonors[0]['amount']);
            if prize.sumdonations and prize.randomdraw:
              if donationSize == 'top' or donationSize == 'above':
                expectedRatio = float(prize.maximumbid / prize.minimumbid);
              else:
                expectedRatio = float(donation.amount / prize.minimumbid);
              self.assertAlmostEqual(expectedRatio, eligibleDonors[0]['weight']);
            else:
              self.assertEqual(1.0, eligibleDonors[0]['weight']);
          result, message = viewutil.draw_prize(prize);
          if donationSize != 'below' or not prize.randomdraw:
            self.assertTrue(result);
            self.assertEqual(donor, prize.winner);
          else:
            self.assertFalse(result);
            self.assertEqual(None, prize.winner);
          donation.delete();
          prize.delete();
    return;
  def test_draw_prize_clears_email_sent(self):
    startRun = self.runsList[28];
    endRun = self.runsList[30];
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=False, randomDraw=True, startRun=startRun, endRun=endRun);
    prize.emailsent = True;
    prize.save();
    donation = randgen.generate_donation(self.rand, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
    donation.save();
    viewutil.draw_prize(prize);
    self.assertFalse(prize.emailsent);
    return;
  def test_draw_prize_multiple_donors_random_nosum(self):
    startRun = self.runsList[28];
    endRun = self.runsList[30];
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=False, randomDraw=True, startRun=startRun, endRun=endRun);
    prize.save();
    donationDonors = {};
    for donor in self.donorList:
      if self.rand.getrandbits(1) == 0:
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
        donation.save();
        donationDonors[donor.id] = donor;
      # Add a few red herrings to make sure out of range donations aren't used
      donation2 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1));
      donation2.save();
      donation3 = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1));
      donation3.save();
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(len(donationDonors.keys()), len(eligibleDonors));
    for eligibleDonor in eligibleDonors:
      found = False;
      if eligibleDonor['donor'] in donationDonors:
        donor = donationDonors[eligibleDonor['donor']];
        donation = donor.donation_set.filter(timereceived__gte=prize.start_draw_time(), timereceived__lte=prize.end_draw_time())[0];
        self.assertEqual(donation.amount, eligibleDonor['amount']);
        self.assertEqual(1.0, eligibleDonor['weight']);
        found = True;
      self.assertTrue(found and "Could not find the donor in the list");
    winners = [];
    for seed in [15634, 12512, 666]:
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertIn(prize.winner.id, donationDonors);
      winners.append(prize.winner);
      current = prize.winner;
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(current, prize.winner);
      prize.winner = None;
      prize.save();
    self.assertNotEqual(winners[0], winners[1]);
    self.assertNotEqual(winners[1], winners[2]);
    self.assertNotEqual(winners[0], winners[2]);
    return;
  def test_draw_prize_multiple_donors_random_sum(self):
    startRun = self.runsList[41];
    endRun = self.runsList[46];
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=True, startRun=startRun, endRun=endRun);
    prize.save();
    donationDonors = {};
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4);
      redHerrings = self.rand.getrandbits(4);
      donationDonors[donor.id] = { 'donor': donor, 'amount': Decimal('0.00') };
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
        donation.save();
        donationDonors[donor.id]['amount'] += donation.amount;
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None;
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1));
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=prize.minimumbid - Decimal('0.10'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1));
        donation.save();
      if donationDonors[donor.id]['amount'] < prize.minimumbid:
        del donationDonors[donor.id];
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(len(donationDonors.keys()), len(eligibleDonors));
    for eligibleDonor in eligibleDonors:
      found = False;
      if eligibleDonor['donor'] in donationDonors:
        entry = donationDonors[eligibleDonor['donor']];
        donor = entry['donor'];
        if entry['amount'] >= prize.minimumbid:
          donations = donor.donation_set.filter(timereceived__gte=prize.start_draw_time(), timereceived__lte=prize.end_draw_time());
          countAmount = Decimal('0.00');
          for donation in donations:
            countAmount += donation.amount;
          self.assertEqual(entry['amount'], eligibleDonor['amount']);
          self.assertEqual(countAmount, eligibleDonor['amount']);
          self.assertAlmostEqual(min(prize.maximumbid / prize.minimumbid, entry['amount'] / prize.minimumbid), Decimal(eligibleDonor['weight']));
          found = True;
    self.assertTrue(found and "Could not find the donor in the list");
    winners = [];
    for seed in [51234, 235426, 62363245]:
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertIn(prize.winner.id, donationDonors);
      winners.append(prize.winner);
      current = prize.winner;
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(current, prize.winner);
      prize.winner = None;
      prize.save();
    self.assertNotEqual(winners[0], winners[1]);
    self.assertNotEqual(winners[1], winners[2]);
    self.assertNotEqual(winners[0], winners[2]);
    return;
  def test_draw_prize_multiple_donors_norandom_nosum(self):
    startRun = self.runsList[25];
    endRun = self.runsList[34];
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=False, randomDraw=False, startRun=startRun, endRun=endRun);
    prize.save();
    largestDonor = None;
    largestAmount = Decimal('0.00');
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4);
      redHerrings = self.rand.getrandbits(4);
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=Decimal('1000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
        donation.save();
        if donation.amount > largestAmount:
          largestDonor = donor;
          largestAmount = donation.amount;
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None;
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1));
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1));
        donation.save();
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(1, len(eligibleDonors));
    self.assertEqual(largestDonor.id, eligibleDonors[0]['donor']);
    self.assertEqual(1.0, eligibleDonors[0]['weight']);
    self.assertEqual(largestAmount, eligibleDonors[0]['amount']);
    for seed in [9524,373, 747]:
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(largestDonor.id, prize.winner.id);
    newDonor = randgen.generate_donor(self.rand);
    newDonor.save();
    newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
    newDonation.save();
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(1, len(eligibleDonors));
    self.assertEqual(newDonor.id, eligibleDonors[0]['donor']);
    self.assertEqual(1.0, eligibleDonors[0]['weight']);
    self.assertEqual(newDonation.amount, eligibleDonors[0]['amount']);
    for seed in [9524,373, 747]:
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(newDonor.id, prize.winner.id);
  def test_draw_prize_multiple_donors_norandom_sum(self):
    startRun = self.runsList[5];
    endRun = self.runsList[9];
    prize = randgen.generate_prize(self.rand, event=self.event, sumDonations=True, randomDraw=False, startRun=startRun, endRun=endRun);
    prize.save();
    donationDonors = {}
    for donor in self.donorList:
      numDonations = self.rand.getrandbits(4);
      redHerrings = self.rand.getrandbits(4);
      donationDonors[donor.id] = { 'donor': donor, 'amount': Decimal('0.00') };
      for i in range(0, numDonations):
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('0.01'), maxAmount=Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
        donation.save();
        donationDonors[donor.id]['amount'] += donation.amount;
      # toss in a few extras to keep the drawer on its toes
      for i in range(0, redHerrings):
        donation = None;
        if self.rand.getrandbits(1) == 0:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=Decimal('2000.00'), maxTime=prize.start_draw_time() - datetime.timedelta(seconds=1));
        else:
          donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=Decimal('1000.01'), maxAmount=prize.minimumbid - Decimal('2000.00'), minTime=prize.end_draw_time() + datetime.timedelta(seconds=1));
        donation.save();
    maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1];
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(1, len(eligibleDonors));
    self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor']);
    self.assertEqual(1.0, eligibleDonors[0]['weight']);
    self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount']);
    for seed in [9524,373, 747]:
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(maxDonor['donor'].id, prize.winner.id);
    oldMaxDonor = maxDonor;
    del donationDonors[oldMaxDonor['donor'].id];
    maxDonor = max(donationDonors.items(), key=lambda x: x[1]['amount'])[1];
    diff = oldMaxDonor['amount'] - maxDonor['amount']
    newDonor = maxDonor['donor'];
    newDonation = randgen.generate_donation(self.rand, donor=newDonor, event=self.event, minAmount=diff + Decimal('0.01'), maxAmount=Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
    newDonation.save();
    maxDonor['amount'] += newDonation.amount;
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(1, len(eligibleDonors));
    self.assertEqual(maxDonor['donor'].id, eligibleDonors[0]['donor']);
    self.assertEqual(1.0, eligibleDonors[0]['weight']);
    self.assertEqual(maxDonor['amount'], eligibleDonors[0]['amount']);
    for seed in [9524,373, 747]:
      prize.winner = None;
      prize.save();
      result, message = viewutil.draw_prize(prize, seed);
      self.assertTrue(result);
      self.assertEqual(maxDonor['donor'].id, prize.winner.id);
  