import binascii
import datetime
import decimal
import os
from decimal import Decimal

import pytz
from tracker.models import (
    Bid,
    Donation,
    DonationBid,
    Donor,
    Event,
    Prize,
    PrizeCategory,
    PrizeKey,
    PrizeWinner,
    SpeedRun,
    Runner,
)
from tracker.models.donation import DonorVisibilityChoices, DonationDomainChoices


def random_name(rand, base):
    return base + str(rand.getrandbits(32))


def random_event_name(rand):
    return random_name(rand, 'event')


def random_first_name(rand):
    return random_name(rand, 'first')


def random_last_name(rand):
    return random_name(rand, 'last')


def random_alias(rand):
    return random_name(rand, 'alias')


def random_email(rand, base):
    return base + '@gmail.com'


def random_paypal_email(rand, base, other_email):
    result = other_email
    while result == other_email:
        result = random_name(rand, base) + '@gmail.com'
    return result


def random_twitch(rand, base):
    return 'http://twitch.tv/' + base


def random_youtube(rand, base):
    return 'http://youtube.com/' + base


def random_website(rand, base):
    return 'http://' + base + '.com'


def random_twitter(rand, base):
    return '@' + base


def random_game_name(rand):
    return 'game' + str(rand.getrandbits(32))


def random_game_description(rand, gamename):
    return 'Description for ' + gamename


def random_prize_name(rand, forGame=None):
    prizename = 'prize' + str(rand.getrandbits(32))
    if forGame:
        prizename = forGame + prizename
    return prizename


def random_prize_description(rand, prizename):
    return 'Description for ' + prizename


def random_bid_description(rand, bidname):
    return 'Description for ' + bidname


def random_amount(rand, *, min_amount=Decimal('0.00'), max_amount=Decimal('10000.00')):
    drange = max_amount - min_amount
    return (min_amount + (drange * Decimal(rand.random()))).quantize(
        Decimal('.01'), rounding=decimal.ROUND_UP
    )


def random_time(rand, start, end):
    delta = end - start
    result = start + datetime.timedelta(
        seconds=rand.randrange(int(delta.total_seconds()))
    )
    return result.astimezone(pytz.utc)


def pick_random_from_queryset(rand, q):
    num = q.count()
    return q[rand.randrange(num)]


def pick_random_element(rand, l):
    return rand.choice(l)


def pick_random_instance(rand, model):
    num = model.objects.all().count()
    if num > 0:
        return model.objects.all()[rand.randrange(num)]
    else:
        return None


def true_false_or_random(rand, value):
    if value is True or value is False:
        return value
    else:
        return bool(rand.getrandbits(1))


def generate_donor(rand, *, firstname=None, lastname=None, alias=None, visibility=None):
    donor = Donor()
    donor.firstname = random_first_name(rand) if firstname is None else firstname
    donor.lastname = random_last_name(rand) if lastname is None else lastname
    alias = random_alias(rand) if alias is None else alias
    donor.visibility = (
        pick_random_element(rand, DonorVisibilityChoices)[0]
        if visibility is None
        else visibility
    )
    if rand.getrandbits(1) or donor.visibility == 'ALIAS':
        donor.alias = alias
    donor.email = random_email(rand, alias)
    if rand.getrandbits(1):
        donor.paypalemail = random_paypal_email(rand, alias, donor.email)
    donor.clean()
    return donor


_DEFAULT_MAX_RUN_LENGTH = 3600 * 6


def generate_run(
    rand, *, event=None, max_run_length=_DEFAULT_MAX_RUN_LENGTH, max_setup_length=600
):
    run = SpeedRun()
    run.name = random_game_name(rand)
    run.description = random_game_description(rand, run.name)
    run.run_time = str(rand.randrange(60, max_run_length))
    run.setup_time = str(rand.randrange(60, max_setup_length))
    if event:
        run.event = event
    else:
        run.event = pick_random_instance(rand, Event)
    run.clean()
    return run


def generate_runner(
    rand, name=None, stream=None, twitter=None, youtube=None, donor=None
):
    runner = Runner(
        name=name or random_name(rand, 'runner'),
        stream=stream or ('https://twitch.tv/%s' % random_name(rand, 'twitch')),
        twitter=twitter or random_name(rand, 'twitter')[:14],
        youtube=youtube or random_name(rand, 'youtube'),
        donor=donor,
    )
    runner.clean()
    return runner


def generate_prize(
    rand,
    *,
    category=None,
    event=None,
    start_run=None,
    end_run=None,
    start_time=None,
    end_time=None,
    sum_donations=None,
    min_amount=Decimal('1.00'),
    max_amount=Decimal('20.00'),
    random_draw=True,
    maxwinners=1,
    state='ACCEPTED',
):
    prize = Prize()
    prize.name = random_prize_name(rand)
    prize.description = random_prize_description(rand, prize.name)
    if start_run:
        prize.startrun = start_run
        prize.endrun = end_run
    elif start_time:
        prize.starttime = start_time
        prize.endtime = end_time
    if category:
        prize.category = category
    else:
        prize.category = pick_random_instance(rand, PrizeCategory)
    if true_false_or_random(rand, sum_donations):
        prize.sumdonations = True
        lo = random_amount(rand, min_amount=min_amount, max_amount=max_amount)
        hi = random_amount(rand, min_amount=min_amount, max_amount=max_amount)
        prize.minimumbid = min(lo, hi)
        prize.maximumbid = max(lo, hi)
    else:
        prize.sumdonations = False
        prize.minimumbid = prize.maximumbid = random_amount(
            rand, min_amount=min_amount, max_amount=max_amount
        )
    prize.randomdraw = random_draw
    if start_run is not None:
        prize.event = start_run.event
    elif event:
        prize.event = event
    else:
        prize.event = pick_random_instance(rand, Event)
    prize.maxwinners = rand.randrange(maxwinners) + 1
    if state:
        prize.state = state
    prize.clean()
    return prize


def generate_prize_key(rand, *, prize=None, key=None, prize_winner=None, winner=None):
    prize_key = PrizeKey()
    prize_key.key = key or '-'.join(
        binascii.b2a_hex(os.urandom(2)).decode('utf-8') for _ in range(4)
    )
    prize_key.prize_id = prize.id if prize else pick_random_instance(rand, Prize).id
    if not prize_winner and winner:
        prize_winner = PrizeWinner.objects.create(prize=prize, winner=winner)
    prize_key.prize_winner = prize_winner
    prize_key.clean()
    return prize_key


def generate_prize_keys(rand, num_keys, *, prize=None):
    if prize is None:
        prize = pick_random_instance(rand, Prize)
    prize_keys = []
    for _ in range(num_keys):
        prize_key = generate_prize_key(rand, prize=prize)
        prize_key.save()
        prize_keys.append(prize_key)
    return prize_keys


def generate_bid(
    rand,
    *,
    allow_children=None,
    min_children=2,
    max_children=5,
    max_depth=2,
    add_goal=None,
    min_goal=Decimal('0.01'),
    max_goal=Decimal('1000.00'),
    run=None,
    event=None,
    parent=None,
    state=None,
    parent_state=None,
):
    bid = Bid()
    bid.description = random_bid_description(rand, bid.name)
    if true_false_or_random(rand, add_goal):
        bid.goal = random_amount(rand, min_amount=min_goal, max_amount=max_goal)
    children = []
    if max_depth > 0 and true_false_or_random(rand, allow_children):
        num_children = rand.randint(min_children, max_children)
        for c in range(0, num_children):
            children.append(
                generate_bid(
                    rand,
                    allow_children=False,
                    max_depth=max_depth - 1,
                    add_goal=add_goal,
                    min_goal=min_goal,
                    max_goal=max_goal,
                    run=run,
                    event=event,
                    parent=bid,
                    state=state,
                )
            )
        bid.istarget = False
    else:
        bid.istarget = True
    if not run and not event and not parent:
        raise Exception('Need at least one of run, event, or parent')
    if parent:
        bid.parent = parent
    if run:
        bid.speedrun = run
    if event:
        bid.event = event
    if parent_state:
        bid.state = parent_state
    elif state:
        bid.state = state
    else:
        if bid.istarget and bid.parent:
            bid.state = pick_random_element(rand, Bid._meta.get_field('state').choices)[
                0
            ]
        else:
            bid.state = pick_random_element(rand, ['HIDDEN', 'OPENED', 'CLOSED'])
    if bid.parent:
        if bid.istarget:
            bid.name = random_name(rand, 'option')
        else:
            bid.name = random_name(rand, 'suboption')
    else:
        if bid.istarget:
            bid.name = random_name(rand, 'challenge')
        else:
            bid.name = random_name(rand, 'choice')
    bid.clean()
    return bid, children


def chain_insert_bid(bid, children):
    bid.clean()
    bid.save()
    for child in children:
        chain_insert_bid(child[0], child[1])


def generate_donation(
    rand,
    *,
    commentstate='APPROVED',
    donor=None,
    no_donor=False,
    domain=None,
    event=None,
    min_amount=Decimal('0.01'),
    max_amount=Decimal('1000.00'),
    min_time=None,
    max_time=None,
    donors=None,
    readstate='READ',
    transactionstate=None,
):
    donation = Donation()
    donation.amount = random_amount(rand, min_amount=min_amount, max_amount=max_amount)
    if event:
        donation.event = event
    else:
        donation.event = pick_random_instance(rand, Event)
    if domain:
        donation.domain = domain
    else:
        donation.domain = pick_random_element(rand, DonationDomainChoices)[0]
    donation.domainId = str(rand.getrandbits(64))
    donation.fee = (donation.amount * Decimal(0.03)).quantize(
        Decimal('0.01'), rounding=decimal.ROUND_UP
    )
    donation.comment = random_name(rand, 'Comment')
    donation.commentstate = commentstate
    donation.readstate = readstate
    if not min_time:
        min_time = event.datetime
    if not max_time:
        max_time = min_time + datetime.timedelta(seconds=60 * 60 * 24 * 14)
    donation.timereceived = random_time(rand, min_time, max_time)
    donation.currency = 'USD'
    donation.transactionstate = transactionstate or 'COMPLETED'
    if donation.domain == 'LOCAL':
        assert (
            donation.transactionstate == 'COMPLETED'
        ), 'Local donations must be specified as COMPLETED'

    if not no_donor:
        if not donor:
            if donors:
                donor = pick_random_element(rand, donors)
            else:
                donor = pick_random_instance(rand, Donor)
        if not donor:
            assert donor, 'No donor provided and none exist'
        donation.donor = donor
    donation.clean()
    return donation


def generate_donation_for_prize(rand, prize, **kwargs):
    event = kwargs.pop('event', prize.event)
    return generate_donation(
        rand,
        min_amount=prize.minimumbid,
        min_time=prize.start_draw_time(),
        max_time=prize.end_draw_time(),
        event=event,
        **kwargs,
    )


def generate_event(rand, start_time=None):
    event = Event()
    if not start_time:
        start_time = datetime.datetime.utcnow().astimezone(pytz.utc)
    event.datetime = start_time
    event.name = random_event_name(rand)
    event.short = event.name
    event.targetamount = Decimal('1000.00')
    event.clean()
    return event


def get_bid_targets(bid, children):
    targets = []
    for child in children:
        targets.extend(get_bid_targets(child[0], child[1]))
    if bid.istarget:
        targets.append(bid)
    return targets


def assign_the_bids(rand, donation, from_set):
    remaining_amount = random_amount(rand, max_amount=donation.amount)
    available_set = set(from_set)
    if len(available_set) == 0:
        return
    while remaining_amount > Decimal('0.00'):
        if (
            remaining_amount < Decimal('1.00')
            or rand.getrandbits(1) == 1
            or len(available_set) == 1
        ):
            use_amount = remaining_amount
        else:
            use_amount = random_amount(
                rand, min_amount=Decimal('1.00'), max_amount=remaining_amount
            )
        remaining_amount = remaining_amount - use_amount
        bid = rand.choice(list(available_set))
        available_set.remove(bid)
        donation_bid = DonationBid.objects.create(
            donation=donation, bid=bid, amount=use_amount
        )
        donation_bid.clean()


def generate_runs(rand, event, num_runs, *, scheduled=False):
    list_of_runs = []
    last_run = event.speedrun_set.last()
    order = last_run.order if (last_run and last_run.order) else 0
    for i in range(0, num_runs):
        run = generate_run(rand, event=event)
        if scheduled:
            order = run.order = order + 1
        run.save()
        list_of_runs.append(run)
    return list_of_runs


def generate_runners(rand, num_runners):
    def save_runner():
        runner = generate_runner(rand)
        runner.save()
        return runner

    return [save_runner() for _ in range(num_runners)]


def generate_donors(rand, num_donors):
    list_of_donors = []
    for i in range(0, num_donors):
        donor = generate_donor(rand)
        donor.save()
        list_of_donors.append(donor)
    return list_of_donors


def generate_bids(
    rand, event, num_bids, *, list_of_runs=None, parent_state=None, state=None
):
    top_bids_list = []
    bid_targets_list = []

    if not list_of_runs:
        list_of_runs = list(SpeedRun.objects.filter(event=event))

    for i in range(0, num_bids):
        if rand.getrandbits(2) <= 2:
            run = pick_random_element(rand, list_of_runs)
        else:
            run = None
        bid, children = generate_bid(
            rand,
            event=None if run else event,
            run=run,
            parent_state=parent_state,
            state=state,
        )
        chain_insert_bid(bid, children)
        top_bids_list.append(bid)
        bid_targets_list.extend(get_bid_targets(bid, children))
    return top_bids_list, bid_targets_list


def generate_prizes(
    rand, event, num_prizes, *, state='ACCEPTED', list_of_runs=None, maxwinners=1
):
    list_of_prizes = []
    if not list_of_runs:
        list_of_runs = list(SpeedRun.objects.filter(event=event).exclude(order=None))
    if not list_of_runs:
        for i in range(num_prizes):
            prize = generate_prize(
                rand, event=event, maxwinners=maxwinners, state=state
            )
            prize.save()
            list_of_prizes.append(prize)
    else:
        num_runs = len(list_of_runs)
        start_time = list_of_runs[0].starttime
        end_time = list_of_runs[-1].endtime
        for i in range(num_prizes):
            if rand.getrandbits(2) <= 2:
                distance = rand.randrange(min(6, num_runs))
                start_run_idx = rand.randrange(num_runs - distance)
                end_run_idx = start_run_idx + distance
                prize = generate_prize(
                    rand,
                    event=event,
                    start_run=list_of_runs[start_run_idx],
                    end_run=list_of_runs[end_run_idx],
                    maxwinners=maxwinners,
                    state=state,
                )
            else:
                time0 = random_time(rand, start_time, end_time)
                time1 = random_time(rand, start_time, end_time)
                start = min(time0, time1)
                end = max(time0, time1)
                prize = generate_prize(
                    rand,
                    event=event,
                    start_time=start,
                    end_time=end,
                    maxwinners=maxwinners,
                    state=state,
                )
            prize.save()
            list_of_prizes.append(prize)
    return list_of_prizes


def generate_donations(
    rand,
    event,
    num_donations,
    *,
    start_time=None,
    end_time=None,
    donors=None,
    assign_bids=True,
    bid_targets_list=None,
    domain=None,
    transactionstate=None,
):
    list_of_donations = []
    if not start_time:
        start_time = event.datetime
    if not end_time:
        run = SpeedRun.objects.filter(event=event).last()
        if not run:
            raise Exception(
                'Need at least one scheduled run with a duration to generate random donations'
            )
        end_time = run.endtime
    if not bid_targets_list:
        bid_targets_list = Bid.objects.filter(istarget=True, event=event)
    if not donors:
        donors = Donor.objects.all() or generate_donors(
            rand, num_donors=num_donations // 2
        )
    for i in range(0, num_donations):
        donation = generate_donation(
            rand,
            event=event,
            min_time=start_time,
            max_time=end_time,
            donors=donors,
            domain=domain,
            transactionstate=transactionstate,
        )
        donation.save()
        if assign_bids:
            assign_the_bids(rand, donation, bid_targets_list)
        list_of_donations.append(donation)
    return list_of_donations


def build_random_event(
    rand,
    *,
    start_time=None,
    num_donors=0,
    num_donations=0,
    num_runs=0,
    num_bids=0,
    num_prizes=0,
):
    if not PrizeCategory.objects.all().exists() and num_prizes > 0:
        PrizeCategory.objects.create(name='Game')
        PrizeCategory.objects.create(name='Grand')
        PrizeCategory.objects.create(name='Grab Bag')

    event = generate_event(rand, start_time=start_time)
    if not start_time:
        start_time = datetime.datetime.combine(event.date, datetime.time()).replace(
            tzinfo=pytz.utc
        )
    event.save()

    list_of_runs = generate_runs(rand, event=event, num_runs=num_runs, scheduled=True)
    last_run_time = list_of_runs[-1].endtime if list_of_runs else start_time
    list_of_donors = generate_donors(rand, num_donors=num_donors)
    top_bids_list, bid_targets_list = generate_bids(
        rand, event=event, num_bids=num_bids, list_of_runs=list_of_runs
    )
    generate_prizes(rand, event=event, num_prizes=num_prizes, list_of_runs=list_of_runs)
    generate_donations(
        rand,
        event=event,
        num_donations=num_donations,
        start_time=start_time,
        end_time=last_run_time,
        donors=list_of_donors,
        assign_bids=True,
        bid_targets_list=bid_targets_list,
    )

    return event
