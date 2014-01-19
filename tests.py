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
from tracker.models import *;
import tracker.viewutil as viewutil;

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
    self.runsList = list(SpeedRun.objects.filter(event=self.event));
    self.donorList = list(Donor.objects.all());
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
          if donationSize == 'below':
            self.assertEqual(0, len(eligibleDonors));
          else:
            self.assertEqual(1, len(eligibleDonors));
            self.assertEqual(donor.id, eligibleDonors[0]['donor']);
            self.assertEqual(donation.amount, eligibleDonors[0]['amount']);
            if prize.sumdonations:
              if donationSize == 'top' or donationSize == 'above':
                expectedRatio = float(prize.maximumbid / prize.minimumbid);
              else:
                expectedRatio = float(donation.amount / prize.minimumbid);
              self.assertAlmostEqual(expectedRatio, eligibleDonors[0]['weight']);
            else:
              self.assertEqual(1.0, eligibleDonors[0]['weight']);
          result, message = viewutil.draw_prize(prize);
          if donationSize != 'below':
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
    prize.sumdonations = False;
    prize.randomdraw = True;
    prize.save();
    donationDonors = [];
    for donor in self.donorList:
      if self.rand.getrandbits(1) == 0:
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid, maxAmount=prize.minimumbid + Decimal('100.00'), minTime=prize.start_draw_time(), maxTime=prize.end_draw_time());
        donation.save();
        donationDonors.append(donor);
    eligibleDonors = prize.eligible_donors();
    self.assertEqual(len(donationDonors), len(eligibleDonors));
    for eligibleDonor in eligibleDonors:
      found = False;
      for donor in donationDonors:
        if donor.id == eligibleDonor['donor']:
          donation = donor.donation_set.all()[0];
          self.assertEqual(donation.amount, eligibleDonor['amount']);
          self.assertEqual(1.0, eligibleDonor['weight']);
          found = True;
      self.assertTrue(found and "Could not find the donor in the list");
      winners = [];
      for seed in [15634, 12512, 666]:
        result, message = viewutil.draw_prize(prize, seed);
        self.assertTrue(result);
        self.assertIn(prize.winner, donationDonors);
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
    pass;
  def test_draw_prize_multiple_donors_norandom_nosum(self):
    pass;
  def test_draw_prize_multiple_donors_norandom_sum(self):
    pass;
  