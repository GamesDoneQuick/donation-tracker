import datetime
import random
from decimal import Decimal

import post_office.models
import pytz
from dateutil.parser import parse as parse_date
from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.test import TestCase
from django.test import TransactionTestCase
from django.urls import reverse

from tracker import models, prizeutil, randgen
from .util import today_noon, MigrationsTestCase


class TestPrizeGameRange(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_prize_range_single(self):
        runs = randgen.generate_runs(self.rand, self.event, 4, scheduled=True)
        run = runs[1]
        prize = randgen.generate_prize(
            self.rand, event=self.event, start_run=run, end_run=run
        )
        prize_runs = prize.games_range()
        self.assertEqual(1, prize_runs.count())
        self.assertEqual(run.id, prize_runs[0].id)

    def test_prize_range_pair(self):
        runs = randgen.generate_runs(self.rand, self.event, 5, scheduled=True)
        start_run = runs[2]
        end_run = runs[3]
        prize = randgen.generate_prize(
            self.rand, event=self.event, start_run=start_run, end_run=end_run
        )
        prize_runs = prize.games_range()
        self.assertEqual(2, prize_runs.count())
        self.assertEqual(start_run.id, prize_runs[0].id)
        self.assertEqual(end_run.id, prize_runs[1].id)

    def test_prize_range_gap(self):
        runs = randgen.generate_runs(self.rand, self.event, 7, scheduled=True)
        runs_slice = runs[2:5]
        prize = randgen.generate_prize(
            self.rand, event=self.event, start_run=runs_slice[0], end_run=runs_slice[-1]
        )
        prize_runs = prize.games_range()
        self.assertEqual(len(runs_slice), prize_runs.count())
        for i in range(0, len(runs_slice)):
            self.assertEqual(runs_slice[i].id, prize_runs[i].id)

    def test_time_prize_no_range(self):
        runs = randgen.generate_runs(self.rand, self.event, 7, scheduled=True)
        event_end = runs[-1].endtime
        time_a = randgen.random_time(self.rand, self.event.datetime, event_end)
        time_b = randgen.random_time(self.rand, self.event.datetime, event_end)
        random_start = min(time_a, time_b)
        random_end = max(time_a, time_b)
        prize = randgen.generate_prize(
            self.rand, event=self.event, start_time=random_start, end_time=random_end
        )
        prize_runs = prize.games_range()
        self.assertEqual(0, prize_runs.count())
        self.assertEqual(random_start, prize.start_draw_time())
        self.assertEqual(random_end, prize.end_draw_time())


class TestPrizeDrawingGeneratedEvent(TransactionTestCase):
    def setUp(self):
        self.event_start = parse_date('2014-01-01 16:00:00Z')
        self.rand = random.Random(516273)
        self.event = randgen.build_random_event(
            self.rand, start_time=self.event_start, num_donors=100, num_runs=50
        )
        self.runs_list = list(models.SpeedRun.objects.filter(event=self.event))
        self.donor_list = list(models.Donor.objects.all())

    def test_draw_random_prize_no_donations(self):
        prize_list = randgen.generate_prizes(
            self.rand, self.event, 50, list_of_runs=self.runs_list
        )
        for prize in prize_list:
            for randomness in [True, False]:
                for use_sum in [True, False]:
                    prize.randomdraw = randomness
                    prize.sumdonations = use_sum
                    prize.save()
                    eligible_donors = prize.eligible_donors()
                    self.assertEqual(0, len(eligible_donors))
                    result, message = prizeutil.draw_prize(prize)
                    self.assertFalse(result)
                    self.assertEqual(0, prize.current_win_count())

    def test_draw_prize_one_donor(self):
        start_run = self.runs_list[14]
        end_run = self.runs_list[28]
        for use_random in [True, False]:
            for use_sum in [True, False]:
                for donation_size in ['top', 'bottom', 'above', 'below', 'within']:
                    prize = randgen.generate_prize(
                        self.rand,
                        event=self.event,
                        sum_donations=use_sum,
                        random_draw=use_random,
                        start_run=start_run,
                        end_run=end_run,
                    )
                    prize.save()
                    donor = randgen.pick_random_element(self.rand, self.donor_list)
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_time=prize.start_draw_time(),
                        max_time=prize.end_draw_time(),
                    )
                    if donation_size == 'above':
                        donation.amount = prize.maximumbid + Decimal('5.00')
                    elif donation_size == 'top':
                        donation.amount = prize.maximumbid
                    elif donation_size == 'within':
                        donation.amount = randgen.random_amount(
                            self.rand,
                            min_amount=prize.minimumbid,
                            max_amount=prize.maximumbid,
                        )
                    elif donation_size == 'bottom':
                        donation.amount = prize.minimumbid
                    elif donation_size == 'below':
                        donation.amount = max(
                            Decimal('0.00'), prize.minimumbid - Decimal('5.00')
                        )
                    donation.save()
                    eligible_donors = prize.eligible_donors()
                    if donation_size == 'below' and prize.randomdraw:
                        self.assertEqual(0, len(eligible_donors))
                    else:
                        self.assertEqual(1, len(eligible_donors))
                        self.assertEqual(donor.id, eligible_donors[0]['donor'])
                        self.assertEqual(donation.amount, eligible_donors[0]['amount'])
                        if prize.sumdonations and prize.randomdraw:
                            if donation_size == 'top' or donation_size == 'above':
                                expected_ratio = float(
                                    prize.maximumbid / prize.minimumbid
                                )
                            else:
                                expected_ratio = float(
                                    donation.amount / prize.minimumbid
                                )
                            self.assertAlmostEqual(
                                expected_ratio, eligible_donors[0]['weight']
                            )
                        else:
                            self.assertEqual(1.0, eligible_donors[0]['weight'])
                    result, message = prizeutil.draw_prize(prize)
                    if donation_size != 'below' or not prize.randomdraw:
                        self.assertTrue(result)
                        self.assertEqual(donor, prize.get_winner())
                    else:
                        self.assertFalse(result)
                        self.assertEqual(None, prize.get_winner())
                    donation.delete()
                    prize.prizewinner_set.all().delete()
                    prize.delete()

    def test_draw_prize_multiple_donors_random_nosum(self):
        start_run = self.runs_list[28]
        end_run = self.runs_list[30]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=True,
            start_run=start_run,
            end_run=end_run,
        )
        prize.save()
        donation_donors = {}
        for donor in self.donor_list:
            if self.rand.getrandbits(1) == 0:
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=prize.minimumbid,
                    max_amount=prize.minimumbid + Decimal('100.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donation_donors[donor.id] = donor
            # Add a few red herrings to make sure out of range donations aren't
            # used
            donation2 = randgen.generate_donation(
                self.rand,
                donor=donor,
                event=self.event,
                min_amount=prize.minimumbid,
                max_amount=prize.minimumbid + Decimal('100.00'),
                max_time=prize.start_draw_time() - datetime.timedelta(seconds=1),
            )
            donation2.save()
            donation3 = randgen.generate_donation(
                self.rand,
                donor=donor,
                event=self.event,
                min_amount=prize.minimumbid,
                max_amount=prize.minimumbid + Decimal('100.00'),
                min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
            )
            donation3.save()
        eligible_donors = prize.eligible_donors()
        self.assertEqual(len(list(donation_donors.keys())), len(eligible_donors))
        for eligible_donor in eligible_donors:
            found = False
            if eligible_donor['donor'] in donation_donors:
                donor = donation_donors[eligible_donor['donor']]
                donation = donor.donation_set.filter(
                    timereceived__gte=prize.start_draw_time(),
                    timereceived__lte=prize.end_draw_time(),
                )[0]
                self.assertEqual(donation.amount, eligible_donor['amount'])
                self.assertEqual(1.0, eligible_donor['weight'])
                found = True
            self.assertTrue(found and 'Could not find the donor in the list')
        winners = []
        for seed in [15634, 12512, 666]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winner().id, donation_donors)
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
        start_run = self.runs_list[41]
        end_run = self.runs_list[46]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=True,
            random_draw=True,
            start_run=start_run,
            end_run=end_run,
        )
        prize.save()
        donation_donors = {}
        for donor in self.donor_list:
            num_donations = self.rand.getrandbits(4)
            red_herrings = self.rand.getrandbits(4)
            donation_donors[donor.id] = {'donor': donor, 'amount': Decimal('0.00')}
            for i in range(0, num_donations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=prize.minimumbid - Decimal('0.10'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donation_donors[donor.id]['amount'] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, red_herrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('0.01'),
                        max_amount=prize.minimumbid - Decimal('0.10'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('0.01'),
                        max_amount=prize.minimumbid - Decimal('0.10'),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
            if donation_donors[donor.id]['amount'] < prize.minimumbid:
                del donation_donors[donor.id]
        eligible_donors = prize.eligible_donors()
        self.assertEqual(len(list(donation_donors.keys())), len(eligible_donors))
        found = False
        for eligible_donor in eligible_donors:
            if eligible_donor['donor'] in donation_donors:
                entry = donation_donors[eligible_donor['donor']]
                donor = entry['donor']
                if entry['amount'] >= prize.minimumbid:
                    donations = donor.donation_set.filter(
                        timereceived__gte=prize.start_draw_time(),
                        timereceived__lte=prize.end_draw_time(),
                    )
                    count_amount = Decimal('0.00')
                    for donation in donations:
                        count_amount += donation.amount
                    self.assertEqual(entry['amount'], eligible_donor['amount'])
                    self.assertEqual(count_amount, eligible_donor['amount'])
                    self.assertAlmostEqual(
                        min(
                            prize.maximumbid / prize.minimumbid,
                            entry['amount'] / prize.minimumbid,
                        ),
                        Decimal(eligible_donor['weight']),
                    )
                    found = True
        # FIXME: what is this actually asserting? it's not very clear to me by glancing at it
        self.assertTrue(found, 'Could not find the donor in the list')
        winners = []
        for seed in [51234, 235426, 62363245]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winner().id, donation_donors)
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
        start_run = self.runs_list[25]
        end_run = self.runs_list[34]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            start_run=start_run,
            end_run=end_run,
        )
        prize.save()
        largest_donor = None
        largest_amount = Decimal('0.00')
        for donor in self.donor_list:
            num_donations = self.rand.getrandbits(4)
            red_herrings = self.rand.getrandbits(4)
            for i in range(0, num_donations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=Decimal('1000.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                if donation.amount > largest_amount:
                    largest_donor = donor
                    largest_amount = donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, red_herrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=Decimal('2000.00'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=max(
                            Decimal('1000.01'), prize.minimumbid - Decimal('2000.00')
                        ),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
        eligible_donors = prize.eligible_donors()
        self.assertEqual(1, len(eligible_donors))
        self.assertEqual(largest_donor.id, eligible_donors[0]['donor'])
        self.assertEqual(1.0, eligible_donors[0]['weight'])
        self.assertEqual(largest_amount, eligible_donors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(largest_donor.id, prize.get_winner().id)
        new_donor = randgen.generate_donor(self.rand)
        new_donor.save()
        new_donation = randgen.generate_donation(
            self.rand,
            donor=new_donor,
            event=self.event,
            min_amount=Decimal('1000.01'),
            max_amount=Decimal('2000.00'),
            min_time=prize.start_draw_time(),
            max_time=prize.end_draw_time(),
        )
        new_donation.save()
        eligible_donors = prize.eligible_donors()
        self.assertEqual(1, len(eligible_donors))
        self.assertEqual(new_donor.id, eligible_donors[0]['donor'])
        self.assertEqual(1.0, eligible_donors[0]['weight'])
        self.assertEqual(new_donation.amount, eligible_donors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(new_donor.id, prize.get_winner().id)

    def test_draw_prize_multiple_donors_norandom_sum(self):
        start_run = self.runs_list[5]
        end_run = self.runs_list[9]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=True,
            random_draw=False,
            start_run=start_run,
            end_run=end_run,
        )
        prize.save()
        donation_donors = {}
        for donor in self.donor_list:
            num_donations = self.rand.getrandbits(4)
            red_herrings = self.rand.getrandbits(4)
            donation_donors[donor.id] = {'donor': donor, 'amount': Decimal('0.00')}
            for i in range(0, num_donations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=Decimal('100.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donation_donors[donor.id]['amount'] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, red_herrings):
                donation = None
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=Decimal('2000.00'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=max(
                            Decimal('1000.01'), prize.minimumbid - Decimal('2000.00')
                        ),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
        max_donor = max(list(donation_donors.items()), key=lambda x: x[1]['amount'])[1]
        eligible_donors = prize.eligible_donors()
        self.assertEqual(1, len(eligible_donors))
        self.assertEqual(max_donor['donor'].id, eligible_donors[0]['donor'])
        self.assertEqual(1.0, eligible_donors[0]['weight'])
        self.assertEqual(max_donor['amount'], eligible_donors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(max_donor['donor'].id, prize.get_winner().id)
        old_max_donor = max_donor
        del donation_donors[old_max_donor['donor'].id]
        max_donor = max(list(donation_donors.items()), key=lambda x: x[1]['amount'])[1]
        diff = old_max_donor['amount'] - max_donor['amount']
        new_donor = max_donor['donor']
        new_donation = randgen.generate_donation(
            self.rand,
            donor=new_donor,
            event=self.event,
            min_amount=diff + Decimal('0.01'),
            max_amount=diff + Decimal('100.00'),
            min_time=prize.start_draw_time(),
            max_time=prize.end_draw_time(),
        )
        new_donation.save()
        max_donor['amount'] += new_donation.amount
        prize = models.Prize.objects.get(id=prize.id)
        eligible_donors = prize.eligible_donors()
        self.assertEqual(1, len(eligible_donors))
        self.assertEqual(max_donor['donor'].id, eligible_donors[0]['donor'])
        self.assertEqual(1.0, eligible_donors[0]['weight'])
        self.assertEqual(max_donor['amount'], eligible_donors[0]['amount'])
        for seed in [9524, 373, 747]:
            prize.prizewinner_set.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(max_donor['donor'].id, prize.get_winner().id)


class TestDonorPrizeEntryDraw(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(9239234)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    def test_single_entry(self):
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

    def test_multiple_entries(self):
        num_donors = 5
        donors = []
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        for i in range(0, num_donors):
            donor = randgen.generate_donor(self.rand)
            donor.save()
            entry = models.DonorPrizeEntry(donor=donor, prize=prize)
            entry.save()
            donors.append(donor.pk)
        eligible = prize.eligible_donors()
        self.assertEqual(num_donors, len(eligible))
        for donor_id in [x['donor'] for x in eligible]:
            self.assertTrue(donor_id in donors)


class TestPrizeMultiWin(TransactionTestCase):
    def setUp(self):
        self.event_start = parse_date('2012-01-01 01:00:00Z')
        self.rand = random.Random()
        self.event = randgen.build_random_event(self.rand, start_time=self.event_start)
        self.event.save()

    def test_win_multi_prize(self):
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
        prize_winner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEqual(1, prize_winner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result, msg)
        prize_winner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEqual(2, prize_winner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result, msg)
        prize_winner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEqual(3, prize_winner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result, msg)

    def test_win_multi_prize_with_accept(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 3
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prize_winner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, acceptcount=1
        )
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prize_winner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEqual(2, prize_winner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)

    def test_win_multi_prize_with_deny(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 3
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prize_winner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, declinecount=1
        )
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prize_winner = models.PrizeWinner.objects.get(winner=donor, prize=prize)
        self.assertEqual(2, prize_winner.pendingcount)
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)

    def test_win_multi_prize_lower_than_max_win(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand)
        prize.event = self.event
        prize.maxwinners = 3
        prize.maxmultiwin = 2
        prize.save()
        models.DonorPrizeEntry.objects.create(donor=donor, prize=prize)
        prize_winner = models.PrizeWinner.objects.create(
            winner=donor, prize=prize, pendingcount=1, declinecount=1
        )
        result, msg = prizeutil.draw_prize(prize)
        self.assertFalse(result)
        donor2 = randgen.generate_donor(self.rand)
        donor2.save()
        models.DonorPrizeEntry.objects.create(donor=donor2, prize=prize)
        result, msg = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        prize_winner = models.PrizeWinner.objects.get(winner=donor2, prize=prize)
        self.assertEqual(1, prize_winner.pendingcount)
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
        target_prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            min_amount=amount,
            max_amount=amount,
            maxwinners=1,
        )
        target_prize.save()
        self.assertEqual(0, len(target_prize.eligible_donors()))
        donor_a = randgen.generate_donor(self.rand)
        donor_a.save()
        donor_b = randgen.generate_donor(self.rand)
        donor_b.save()
        donation_a = randgen.generate_donation(
            self.rand,
            donor=donor_a,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        donation_a.save()
        self.assertEqual(1, len(target_prize.eligible_donors()))
        self.assertEqual(donor_a.id, target_prize.eligible_donors()[0]['donor'])
        prizeutil.draw_prize(target_prize)
        self.assertEqual(donor_a, target_prize.get_winner())
        self.assertEqual(0, len(target_prize.eligible_donors()))
        donation_b = randgen.generate_donation(
            self.rand,
            donor=donor_b,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        donation_b.save()
        self.assertEqual(1, len(target_prize.eligible_donors()))
        self.assertEqual(donor_b.id, target_prize.eligible_donors()[0]['donor'])
        prize_winner_entry = target_prize.prizewinner_set.filter(winner=donor_a)[0]
        prize_winner_entry.pendingcount = 0
        prize_winner_entry.declinecount = 1
        prize_winner_entry.save()
        self.assertEqual(1, len(target_prize.eligible_donors()))
        self.assertEqual(donor_b.id, target_prize.eligible_donors()[0]['donor'])
        prizeutil.draw_prize(target_prize)
        self.assertEqual(donor_b, target_prize.get_winner())
        self.assertEqual(1, target_prize.current_win_count())
        self.assertEqual(0, len(target_prize.eligible_donors()))

    def test_cannot_exceed_max_winners(self):
        target_prize = randgen.generate_prize(self.rand, event=self.event)
        target_prize.maxwinners = 2
        target_prize.save()
        num_donors = 4
        donors = []
        for i in range(0, num_donors):
            donor = randgen.generate_donor(self.rand)
            donor.save()
            donors.append(donor)
        winner0 = models.PrizeWinner(winner=donors[0], prize=target_prize)
        winner0.clean()
        winner0.save()
        winner1 = models.PrizeWinner(winner=donors[1], prize=target_prize)
        winner1.clean()
        winner1.save()
        with self.assertRaises(ValidationError):
            winner2 = models.PrizeWinner(winner=donors[2], prize=target_prize)
            winner2.clean()
        winner0.pendingcount = 0
        winner0.declinecount = 1
        winner0.save()
        winner2.clean()
        winner2.save()


class TestPrizeCountryFilter(TransactionTestCase):
    fixtures = ['countries']

    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.build_random_event(self.rand)
        self.event.save()

    def test_country_filter_event(self):
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
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

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

    def test_country_filter_prize(self):
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
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()
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

    def test_country_region_blacklist_filter_event(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowed_state = 'StateOne'
        disallowed_state = 'StateTwo'
        for state in [allowed_state, disallowed_state]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        country_region = models.CountryRegion.objects.create(
            country=country, name=disallowed_state
        )
        self.event.disallowed_prize_regions.add(country_region)
        self.event.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[1]))
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))

    def test_country_region_blacklist_filter_prize(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowed_state = 'StateOne'
        disallowed_state = 'StateTwo'
        for state in [allowed_state, disallowed_state]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        country_region = models.CountryRegion.objects.create(
            country=country, name=disallowed_state
        )
        prize.disallowed_prize_regions.add(country_region)
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
        target_prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            min_amount=amount,
            max_amount=amount,
            maxwinners=1,
        )
        target_prize.save()
        winner = randgen.generate_donor(self.rand)
        winner.save()
        winning_donation = randgen.generate_donation(
            self.rand,
            donor=winner,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        winning_donation.save()
        self.assertEqual(1, len(target_prize.eligible_donors()))
        self.assertEqual(winner.id, target_prize.eligible_donors()[0]['donor'])
        self.assertEqual(0, len(prizeutil.get_past_due_prize_winners(self.event)))
        current_date = datetime.date.today()
        result, status = prizeutil.draw_prize(target_prize)
        prize_win = models.PrizeWinner.objects.get(prize=target_prize)
        self.assertEqual(
            prize_win.accept_deadline_date(),
            current_date
            + datetime.timedelta(days=self.event.prize_accept_deadline_delta),
        )

        prize_win.acceptdeadline = datetime.datetime.utcnow().replace(
            tzinfo=pytz.utc
        ) - datetime.timedelta(days=2)
        prize_win.save()
        self.assertEqual(0, len(target_prize.eligible_donors()))
        past_due = prizeutil.get_past_due_prize_winners(self.event)
        self.assertEqual(1, len(prizeutil.get_past_due_prize_winners(self.event)))
        self.assertEqual(prize_win, past_due[0])


class TestBackfillPrevNextMigrations(MigrationsTestCase):
    migrate_from = '0001_squashed_0020_add_runner_pronouns_and_platform'
    migrate_to = '0003_populate_prev_next_run'

    def setUpBeforeMigration(self, apps):  # noqa N806
        Prize = apps.get_model('tracker', 'Prize')  # noqa N806
        Event = apps.get_model('tracker', 'Event')  # noqa N806
        SpeedRun = apps.get_model('tracker', 'SpeedRun')  # noqa N806
        self.rand = random.Random(None)
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon, targetamount=100
        )
        self.run1 = SpeedRun.objects.create(
            event=self.event, name='Test Run 1', order=1, run_time='0:05:00'
        )
        self.run2 = SpeedRun.objects.create(
            event=self.event, name='Test Run 2', order=2, run_time='0:05:00'
        )
        self.run3 = SpeedRun.objects.create(
            event=self.event, name='Test Run 3', order=3, run_time='0:05:00'
        )
        self.prize1 = Prize.objects.create(
            event=self.event, name='Test Prize 1', startrun=self.run1, endrun=self.run1
        )
        self.prize2 = Prize.objects.create(
            event=self.event, name='Test Prize 2', startrun=self.run2, endrun=self.run2
        )
        self.prize3 = Prize.objects.create(
            event=self.event, name='Test Prize 3', startrun=self.run3, endrun=self.run3
        )

    def test_prev_next_backfilled(self):
        Prize = self.apps.get_model('tracker', 'Prize')  # noqa N806
        prize1 = Prize.objects.get(pk=self.prize1.id)
        prize2 = Prize.objects.get(pk=self.prize2.id)
        prize3 = Prize.objects.get(pk=self.prize3.id)
        self.assertEqual(prize1.prev_run_id, None, 'prize 1 prev run incorrect')
        self.assertEqual(prize1.next_run_id, self.run2.id, 'prize 1 next run incorrect')
        self.assertEqual(prize2.prev_run_id, self.run1.id, 'prize 2 prev run incorrect')
        self.assertEqual(prize2.next_run_id, self.run3.id, 'prize 2 next run incorrect')
        self.assertEqual(prize3.prev_run_id, self.run2.id, 'prize 3 prev run incorrect')
        self.assertEqual(prize3.next_run_id, None, 'prize 3 next run incorrect')


class TestPrizeSignals(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.runs = randgen.generate_runs(self.rand, self.event, 4, scheduled=True)
        self.event_prize = models.Prize.objects.create(
            name='Event Wide Prize', startrun=self.runs[0], endrun=self.runs[3]
        )
        self.start_prize = models.Prize.objects.create(
            name='Start Prize', startrun=self.runs[0], endrun=self.runs[0]
        )
        self.middle_prize = models.Prize.objects.create(
            name='Middle Prize', startrun=self.runs[1], endrun=self.runs[1]
        )
        self.end_prize = models.Prize.objects.create(
            name='End Prize', startrun=self.runs[3], endrun=self.runs[3]
        )
        self.start_span_prize = models.Prize.objects.create(
            name='Start Span Prize', startrun=self.runs[0], endrun=self.runs[1]
        )
        self.middle_span_prize = models.Prize.objects.create(
            name='Middle Span Prize', startrun=self.runs[1], endrun=self.runs[2]
        )
        self.end_span_prize = models.Prize.objects.create(
            name='End Span Prize', startrun=self.runs[2], endrun=self.runs[3]
        )

    def refresh_all(self):
        for model in [
            self.event,
            self.event_prize,
            self.start_prize,
            self.middle_prize,
            self.end_prize,
            self.start_span_prize,
            self.middle_span_prize,
            self.end_span_prize,
        ] + self.runs:
            try:
                model.refresh_from_db()
            except ObjectDoesNotExist:
                pass  # deleted as part of test

    def test_initial_state(self):
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_run_inserted(self):
        self.runs[3].order = 5
        self.runs[3].save()
        self.runs[2].order = 4
        self.runs[2].save()
        self.new_run = models.SpeedRun(
            event=self.event, name='New Run', run_time='0:05:00', order=3
        )
        self.new_run.save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.new_run)
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.new_run)
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.new_run)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_first_run_removed_from_order(self):
        self.runs[0].order = None
        self.runs[0].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, None)
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_first_run_deleted(self):
        self.event_prize.startrun = self.runs[1]
        self.event_prize.save()
        self.start_prize.delete()
        self.start_span_prize.delete()
        self.runs[0].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_second_run_removed_from_order(self):
        self.runs[1].order = None
        self.runs[1].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, None)
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_second_run_deleted(self):
        self.start_span_prize.delete()
        self.middle_prize.delete()
        self.middle_span_prize.delete()
        self.runs[1].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_third_run_removed_from_order(self):
        self.runs[2].order = None
        self.runs[2].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[3])
        self.assertEqual(self.end_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[3])
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, None)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_third_run_deleted(self):
        self.middle_span_prize.delete()
        self.end_span_prize.delete()
        self.runs[2].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[3])
        self.assertEqual(self.end_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[3])

    def test_fourth_run_removed_from_order(self):
        self.runs[3].order = None
        self.runs[3].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, None)
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, None)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_fourth_run_deleted(self):
        self.end_prize.delete()
        self.end_span_prize.delete()
        self.event_prize.endrun = self.runs[2]
        self.event_prize.save()
        self.runs[3].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, None)


class TestPrizeTimeRange(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.runs = randgen.generate_runs(self.rand, self.event, 4, scheduled=True)


class TestPrizeKey(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.run = randgen.generate_run(self.rand, event=self.event)
        self.run.order = 1
        self.run.save()
        self.prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            start_run=self.run,
            end_run=self.run,
            random_draw=True,
        )
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
        donor_count = self.prize_keys.count() // 2
        models.Donor.objects.bulk_create(
            [randgen.generate_donor(self.rand) for _ in range(donor_count)]
        )
        # only Postgres returns the objects with pks, so refetch
        donors = list(models.Donor.objects.order_by('-id')[:donor_count])
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(
                    self.rand, donor=d, prize=self.prize
                )
                for d in donors
            ]
        )
        self.assertSetEqual(
            {d['donor'] for d in self.prize.eligible_donors()}, {d.id for d in donors}
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertSetEqual(set(result['winners']), {d.id for d in donors})
        self.assertSetEqual(
            {k.winner.id for k in self.prize_keys if k.winner}, {d.id for d in donors}
        )
        for key in self.prize_keys:
            if not key.winner:
                continue
            self.assertIn(key.winner, donors, '%s was not in donors.' % key.winner)
            self.assertEqual(key.prize_winner.pendingcount, 0)
            self.assertEqual(key.prize_winner.acceptcount, 1)
            self.assertEqual(key.prize_winner.declinecount, 0)
            self.assertTrue(key.prize_winner.emailsent)
            self.assertEqual(key.prize_winner.acceptemailsentcount, 1)
            self.assertEqual(key.prize_winner.shippingstate, 'SHIPPED')
            self.assertFalse(key.prize_winner.shippingemailsent)

    def test_draw_with_claimed_keys(self):
        self.prize.save()
        donor_count = self.prize_keys.count() // 2
        models.Donor.objects.bulk_create(
            [randgen.generate_donor(self.rand) for _ in range(donor_count)]
        )
        # only Postgres returns the objects with pks, so refetch
        old_donors = set(models.Donor.objects.order_by('-id')[:donor_count])
        old_ids = {d.id for d in old_donors}
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(
                    self.rand, donor=d, prize=self.prize
                )
                for d in old_donors
            ]
        )
        self.assertSetEqual(
            {d['donor'] for d in self.prize.eligible_donors()},
            {d.id for d in old_donors},
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        models.Donor.objects.bulk_create(
            [randgen.generate_donor(self.rand) for _ in range(donor_count)]
        )
        new_donors = set(models.Donor.objects.order_by('-id')[:donor_count])
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(
                    self.rand, donor=d, prize=self.prize
                )
                for d in new_donors
            ]
        )
        self.assertSetEqual(
            {d['donor'] for d in self.prize.eligible_donors()},
            {d.id for d in new_donors},
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertSetEqual(set(result['winners']), {d.id for d in new_donors})
        self.assertSetEqual(
            {k.winner.id for k in self.prize_keys if k.winner},
            old_ids | {d.id for d in new_donors},
        )
        all_donors = old_donors | new_donors
        for key in self.prize_keys:
            self.assertIn(key.winner, all_donors, '%s was not in donors.' % key.winner)
            self.assertEqual(key.prize_winner.pendingcount, 0)
            self.assertEqual(key.prize_winner.acceptcount, 1)
            self.assertEqual(key.prize_winner.declinecount, 0)
            self.assertTrue(key.prize_winner.emailsent)
            self.assertEqual(key.prize_winner.acceptemailsentcount, 1)
            self.assertEqual(key.prize_winner.shippingstate, 'SHIPPED')
            self.assertFalse(key.prize_winner.shippingemailsent)

    def test_more_donors_than_keys(self):
        self.prize.save()
        donor_count = self.prize_keys.count() * 2
        models.Donor.objects.bulk_create(
            [randgen.generate_donor(self.rand) for _ in range(donor_count)]
        )
        # only Postgres returns the objects with pks, so refetch
        donors = list(models.Donor.objects.order_by('id')[:donor_count])
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(
                    self.rand, donor=d, prize=self.prize
                )
                for d in donors
            ]
        )
        self.assertSetEqual(
            {d['donor'] for d in self.prize.eligible_donors()}, {d.id for d in donors}
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertEqual(self.prize.prizewinner_set.count(), self.prize_keys.count())
        for key in self.prize_keys:
            self.assertIn(
                key.winner, donors, '%s was not in eligible donors.' % key.winner
            )
            self.assertIn(
                key.winner.id, result['winners'], '%s was not in winners.' % key.winner
            )
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
        self.assertNotEqual(
            sorted(w.winner.id for w in self.prize.prizewinner_set.all()), old_donors
        )


class TestPrizeAdmin(TestCase):
    # TODO: util?
    def assertMessages(self, response, messages):  # noqa N806
        self.assertSetEqual(
            {str(m) for m in response.wsgi_request._messages}, set(messages)
        )

    def setUp(self):
        self.staff_user = User.objects.create_user(
            'staff', 'staff@example.com', 'staff'
        )
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event)
        self.prize.maximumbid = self.prize.minimumbid + 5
        self.prize.save()
        # TODO: janky place to test this behavior, but it'll do for now
        self.assertEqual(self.prize.minimumbid, self.prize.maximumbid)
        self.prize_with_keys = randgen.generate_prize(self.rand, event=self.event)
        self.prize_with_keys.key_code = True
        self.prize_with_keys.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.prize_winner = models.PrizeWinner.objects.create(
            winner=self.donor, prize=self.prize
        )
        self.donor_prize_entry = models.DonorPrizeEntry.objects.create(
            donor=self.donor, prize=self.prize
        )
        self.prize_key = models.PrizeKey.objects.create(
            prize=self.prize_with_keys, key='dead-beef-dead-beef'
        )

    def test_prize_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prize_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prize_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prize_change', args=(self.prize.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_prize_key_import_action(self):
        self.client.login(username='admin', password='password')

        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'import_keys_action',
                ACTION_CHECKBOX_NAME: [self.prize.id, self.prize_with_keys.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {'action': 'import_keys_action', ACTION_CHECKBOX_NAME: [self.prize.id]},
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'import_keys_action',
                ACTION_CHECKBOX_NAME: [self.prize_with_keys.id],
            },
        )
        self.assertRedirects(
            response,
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
        )

    def test_prize_key_import_form(self):
        keys = ['dead-beef-dead-beef-123%d' % i for i in range(5)]
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password')
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize.id,))
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Cannot import prize keys to non key prizes.'])

        response = self.client.get(
            reverse(
                'admin:tracker_prize_key_import', args=(self.prize_with_keys.id + 1,)
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 200)

        keys_input = (
            '\n' + ' \n '.join(keys) + '\n%s\n\n' % keys[0]
        )  # test whitespace stripping and deduping
        response = self.client.post(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
            {'keys': keys_input},
        )

        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['5 key(s) added to prize.'])
        self.prize_with_keys.refresh_from_db()
        self.assertEqual(self.prize_with_keys.maxwinners, 6)
        self.assertEqual(self.prize_with_keys.prizekey_set.count(), 6)
        self.assertSetEqual(
            set(keys), {key.key for key in self.prize_with_keys.prizekey_set.all()[1:]}
        )

        response = self.client.post(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
            {'keys': keys[0]},
        )
        self.assertFormError(
            response, 'form', 'keys', ['At least one key already exists.']
        )

    def test_prize_winner_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prizewinner_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prizewinner_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizewinner_change', args=(self.prize_winner.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_donor_prize_entry_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_donorprizeentry_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donorprizeentry_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse(
                'admin:tracker_donorprizeentry_change',
                args=(self.donor_prize_entry.id,),
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_prize_key_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prizekey_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prizekey_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizekey_change', args=(self.prize_key.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_prize_mail_preview(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse('admin:preview_prize_winner_mail', args=(self.prize_winner.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post_office.models.Email.objects.count(), 0)


class TestPrizeList(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_prize_list(self):
        regular_prize = randgen.generate_prize(
            self.rand, event=self.event, maxwinners=2
        )
        regular_prize.save()
        donors = randgen.generate_donors(self.rand, 2)
        for d in donors:
            models.PrizeWinner.objects.create(prize=regular_prize, winner=d)
        key_prize = randgen.generate_prize(self.rand, event=self.event)
        key_prize.key_code = True
        key_prize.save()
        key_winners = randgen.generate_donors(self.rand, 50)
        prize_keys = randgen.generate_prize_keys(self.rand, 50, prize=key_prize)
        for w, k in zip(key_winners, prize_keys):
            k.prize_winner = models.PrizeWinner.objects.create(
                prize=key_prize, winner=w
            )
            k.save()

        response = self.client.get(reverse('tracker:prizeindex', args=(self.event.id,)))
        self.assertContains(response, donors[0].visible_name())
        self.assertContains(response, donors[1].visible_name())
        self.assertContains(response, '50 winner(s)')
        self.assertNotContains(response, 'Invalid Variable')


class TestPrizeWinner(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()
        randgen.generate_runs(self.rand, self.event, 1, scheduled=True)
        self.write_in_prize = randgen.generate_prizes(self.rand, self.event, 1)[0]
        self.write_in_donor = randgen.generate_donors(self.rand, 1)[0]
        models.PrizeWinner.objects.create(
            prize=self.write_in_prize, winner=self.write_in_donor, acceptcount=1
        )
        self.donation_prize = randgen.generate_prizes(self.rand, self.event, 1)[0]
        self.donation_donor = randgen.generate_donors(self.rand, 1)[0]
        models.Donation.objects.create(
            event=self.event,
            donor=self.donation_donor,
            transactionstate='COMPLETED',
            amount=5,
        )
        models.PrizeWinner.objects.create(
            prize=self.donation_prize, winner=self.donation_donor, acceptcount=1
        )

    def test_donor_cache(self):
        self.assertEqual(
            self.write_in_prize.get_prize_winner().donor_cache, self.write_in_donor
        )
        self.assertEqual(
            self.donation_prize.get_prize_winner().donor_cache,
            self.donation_donor.cache_for(self.event.id),
        )
