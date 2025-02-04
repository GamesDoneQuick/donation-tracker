import binascii
import datetime
import decimal
import os
import random
from decimal import Decimal

from tracker.models import (
    Ad,
    Bid,
    Donation,
    DonationBid,
    Donor,
    Event,
    Interstitial,
    Interview,
    Milestone,
    Prize,
    PrizeCategory,
    PrizeKey,
    PrizeWinner,
    SpeedRun,
    Talent,
)
from tracker.models.donation import DonationDomainChoices, DonorVisibilityChoices
from tracker.util import utcnow


def random_name(rand: random.Random, base):
    return base + str(rand.getrandbits(32))


def random_event_name(rand: random.Random):
    return random_name(rand, 'event')


def random_first_name(rand: random.Random):
    return random_name(rand, 'first')


def random_last_name(rand: random.Random):
    return random_name(rand, 'last')


def random_alias(rand: random.Random):
    return random_name(rand, 'alias')


def random_email(rand: random.Random, base):
    return random_name(rand, base) + '@gmail.com'


def random_paypal_email(rand: random.Random, base, other_email):
    result = other_email
    while result == other_email:
        result = random_name(rand, base) + '@gmail.com'
    return result


def random_twitch(rand: random.Random, base):
    return 'http://twitch.tv/' + base


def random_youtube(rand: random.Random, base):
    return 'http://youtube.com/' + base


def random_website(rand: random.Random, base):
    return 'http://' + base + '.com'


def random_twitter(rand: random.Random, base):
    return '@' + base


def random_game_name(rand):
    return 'game' + str(rand.getrandbits(32))


def random_game_description(rand: random.Random, gamename):
    return 'Description for ' + gamename


def random_prize_name(rand: random.Random, forGame=None):
    prizename = 'prize' + str(rand.getrandbits(32))
    if forGame:
        prizename = forGame + prizename
    return prizename


def random_prize_description(rand: random.Random, prizename):
    return 'Description for ' + prizename


def random_bid_description(rand: random.Random, bidname):
    return 'Description for ' + bidname


def random_amount(
    rand: random.Random, *, min_amount=Decimal('0.00'), max_amount=Decimal('10000.00')
):
    drange = max_amount - min_amount
    return (min_amount + (drange * Decimal(rand.random()))).quantize(
        Decimal('.01'), rounding=decimal.ROUND_UP
    )


def random_time(rand: random.Random, start, end):
    delta = end - start
    result = start + datetime.timedelta(
        seconds=rand.randrange(int(delta.total_seconds()))
    )
    return result.astimezone(datetime.timezone.utc)


def true_false_or_random(rand: random.Random, value):
    if value is True or value is False:
        return value
    else:
        return bool(rand.getrandbits(1))


def generate_donor(
    rand: random.Random, *, firstname=None, lastname=None, alias=None, visibility=None
):
    donor = Donor()
    donor.firstname = firstname or random_first_name(rand)
    donor.lastname = lastname or random_last_name(rand)
    donor.visibility = visibility or rand.choice(DonorVisibilityChoices)[0]
    provided_alias = alias
    alias = alias or random_alias(rand)
    if donor.visibility == 'ALIAS' or provided_alias:
        # don't actually assign an alias unless we need it
        donor.alias = alias
    donor.email = random_email(rand, alias)
    if rand.getrandbits(1):
        donor.paypalemail = random_paypal_email(rand, alias, donor.email)
    donor.full_clean()
    return donor


_DEFAULT_MAX_RUN_LENGTH = 3600 * 6


def generate_run(
    rand,
    *,
    event=None,
    max_run_length=_DEFAULT_MAX_RUN_LENGTH,
    max_setup_length=600,
    ordered=False,
):
    run = SpeedRun()
    run.name = random_game_name(rand)
    run.description = random_game_description(rand, run.name)
    run.run_time = str(rand.randrange(60, max_run_length))
    run.setup_time = str(rand.randrange(60, max_setup_length))
    if event:
        run.event = event
    else:
        run.event = rand.choice(Event.objects.all())
        assert run.event, 'need at least one event'
    if ordered:
        last = run.event.speedrun_set.last()
        run.order = last.order + 1 if last else 1
    run.full_clean()
    return run


def generate_talent(
    rand, name=None, stream=None, twitter=None, youtube=None, donor=None
):
    if callable(name):
        name = name()
    talent = Talent(
        name=name or random_name(rand, 'talent'),
        stream=stream or ('https://twitch.tv/%s' % random_name(rand, 'twitch')),
        twitter=twitter or random_name(rand, 'twitter')[:14],
        youtube=youtube or random_name(rand, 'youtube'),
        donor=donor,
    )
    talent.full_clean()
    return talent


# convenience to make them easier to distinguish in test failures


def generate_runner(rand, name=None, **kwargs):
    return generate_talent(rand, name=name or random_name(rand, 'runner'), **kwargs)


def generate_host(rand, name=None, **kwargs):
    return generate_talent(rand, name=name or random_name(rand, 'host'), **kwargs)


def generate_commentator(rand, name=None, **kwargs):
    return generate_talent(
        rand, name=name or random_name(rand, 'commentator'), **kwargs
    )


def generate_interviewer(rand, name=None, **kwargs):
    return generate_talent(
        rand, name=name or random_name(rand, 'interviewer'), **kwargs
    )


def generate_subject(rand, name=None, **kwargs):
    return generate_talent(rand, name=name or random_name(rand, 'subject'), **kwargs)


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
    random_draw=True,
    maxwinners=1,
    state='ACCEPTED',
    handler=None,
):
    from django.contrib.auth.models import User

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
        prize.category = rand.choice([None] + list(PrizeCategory.objects.all()))
    prize.sumdonations = true_false_or_random(rand, sum_donations)
    prize.minimumbid = min_amount
    prize.randomdraw = random_draw
    if start_run:
        prize.event = start_run.event
    elif event:
        prize.event = event
    else:
        prize.event = rand.choice(Event.objects.all())
    prize.maxwinners = rand.randrange(maxwinners) + 1
    if state:
        prize.state = state
    prize.handler = handler or User.objects.get_or_create(username='prizehandler')[0]
    prize.full_clean()
    return prize


def generate_prize_key(
    rand: random.Random, *, prize=None, key=None, prize_winner=None, winner=None
):
    prize_key = PrizeKey()
    prize_key.key = key or '-'.join(
        binascii.b2a_hex(os.urandom(2)).decode('utf-8') for _ in range(4)
    )
    prize_key.prize_id = prize.id if prize else rand.choice(Prize.objects.all()).id
    if not prize_winner and winner:
        prize_winner = PrizeWinner.objects.create(prize=prize, winner=winner)
    prize_key.prize_winner = prize_winner
    prize_key.full_clean()
    return prize_key


def generate_prize_keys(rand: random.Random, num_keys, *, prize=None):
    if prize is None:
        prize = rand.choice(Prize.objects.all())
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
    allowuseroptions=None,
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
    assert run or event or parent, 'Need at least one of run, event, or parent'
    if state in ['PENDING', 'DENIED']:
        if parent_state is not None:
            allowuseroptions = True
            max_depth = min(max_depth, 1)
        else:
            assert parent, 'Need to provide parent for pending or denied bids'
            assert parent.allowuseroptions, 'Parent does not support user options'
            allowuseroptions = False
            allow_children = False
    if allowuseroptions is not None:
        bid.allowuseroptions = allowuseroptions
    if parent:
        bid.parent = parent
        bid.speedrun = parent.speedrun
        bid.event = parent.event
    elif run:
        bid.speedrun = run
        bid.event = run.event
    else:
        bid.event = event
    children = []
    assert 0 <= min_children <= max_children
    if max_depth > 0 and true_false_or_random(rand, allowuseroptions or allow_children):
        num_children = rand.randint(min_children, max_children)
        for c in range(0, num_children):
            children.append(
                generate_bid(
                    rand,
                    allow_children=max_depth > 1,
                    max_depth=max_depth - 1,
                    add_goal=add_goal,
                    min_goal=min_goal,
                    max_goal=max_goal,
                    run=run,
                    event=event,
                    parent=bid,
                    state=(
                        state
                        if state is not None
                        else (
                            rand.choice([bid.state, 'DENIED', 'PENDING'])
                            if allowuseroptions
                            else bid.state
                        )
                    ),
                )
            )
        bid.istarget = False
    else:
        bid.istarget = True
    # FIXME: this is a little confusingly named because 'state' really means 'children_state' if 'parent_state' is specified
    if parent_state:
        bid.state = parent_state
    elif state:
        bid.state = state
    else:
        if bid.istarget and bid.parent and bid.parent.allowuseroptions:
            bid.state = rand.choice(Bid._meta.get_field('state').choices)[0]
        else:
            bid.state = rand.choice(['HIDDEN', 'OPENED', 'CLOSED'])
    if bid.parent:
        if bid.istarget:
            bid.name = random_name(rand, 'option')
        else:
            bid.name = random_name(rand, 'suboption')
    else:
        if true_false_or_random(rand, add_goal):
            bid.goal = random_amount(rand, min_amount=min_goal, max_amount=max_goal)
        if bid.istarget:
            bid.name = random_name(rand, 'challenge')
        else:
            bid.name = random_name(rand, 'choice')
    bid.full_clean()
    return bid, children


def chain_insert_bid(bid, children):
    bid.full_clean()
    bid.save()
    for child in children:
        chain_insert_bid(child[0], child[1])


def generate_donation(
    rand,
    *,
    commentstate='APPROVED',
    donor=None,
    donors=None,
    no_donor=False,
    domain=None,
    event=None,
    min_amount=Decimal('0.01'),
    max_amount=Decimal('1000.00'),
    min_time=None,
    max_time=None,
    readstate='READ',
    transactionstate=None,
):
    donation = Donation()
    donation.amount = random_amount(rand, min_amount=min_amount, max_amount=max_amount)
    if not event:
        event = rand.choice(Event.objects.all())
    assert event, 'No event provided and none exist'
    donation.event = event
    if domain:
        donation.domain = domain
    else:
        donation.domain = rand.choice(DonationDomainChoices)[0]
    donation.domainId = str(rand.getrandbits(64))
    donation.fee = (donation.amount * Decimal(0.03)).quantize(
        Decimal('0.01'), rounding=decimal.ROUND_UP
    )
    if commentstate != 'ABSENT':
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
        if donor is None:
            if donors:
                donor = rand.choice(donors)
            else:
                assert Donor.objects.exists(), 'No donor provided and none exist'
                donor = rand.choice(Donor.objects.all())
        donation.donor = donor
    donation.full_clean()
    return donation


def generate_donation_for_prize(
    rand, prize, *, min_amount=None, min_time=None, max_time=None, **kwargs
):
    event = kwargs.pop('event', prize.event)
    return generate_donation(
        rand,
        min_amount=prize.minimumbid,
        min_time=prize.start_draw_time(),
        max_time=prize.end_draw_time(),
        event=event,
        **kwargs,
    )


def generate_event(rand: random.Random, start_time=None):
    event = Event()
    if not start_time:
        start_time = utcnow()
    event.datetime = start_time
    event.name = random_event_name(rand)
    event.short = event.name
    event.paypalemail = 'receiver@example.com'
    event.full_clean()
    return event


def get_bid_targets(bid, children):
    targets = []
    for child in children:
        targets.extend(get_bid_targets(child[0], child[1]))
    if bid.istarget:
        targets.append(bid)
    return targets


def generate_runs(rand: random.Random, event, num_runs, *, ordered=False):
    list_of_runs = []
    for i in range(0, num_runs):
        run = generate_run(rand, event=event, ordered=ordered)
        run.save()
        list_of_runs.append(run)
    return list_of_runs


def generate_runners(rand: random.Random, num_runners):
    def save_runner():
        runner = generate_talent(rand)
        runner.save()
        return runner

    return [save_runner() for _ in range(num_runners)]


def generate_donors(rand: random.Random, num_donors):
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
            run = rand.choice(list_of_runs)
        else:
            run = None
        bid, children = generate_bid(
            rand,
            event=event,
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
    no_donor=False,
    always_assign_bids=False,
    assign_bids=True,
    bid_targets_list=None,
    domain=None,
    transactionstate=None,
    readstate='READ',
    commentstate='APPROVED',
):
    if not start_time:
        start_time = event.datetime
    if not end_time:
        run = SpeedRun.objects.filter(event=event).last()
        assert (
            run
        ), 'Need at least one scheduled run with a duration to generate random donations'
        end_time = run.endtime
    if not donors and not no_donor:
        donors = Donor.objects.all() or generate_donors(
            rand, num_donors=num_donations // 2
        )

    def save_donation():
        donation = generate_donation(
            rand,
            event=event,
            min_time=start_time,
            max_time=end_time,
            donors=donors,
            no_donor=no_donor,
            domain=domain,
            transactionstate=transactionstate,
            readstate=readstate,
            commentstate=commentstate,
        )
        donation.save()
        return donation

    donations = [save_donation() for _ in range(num_donations)]
    if assign_bids:
        if not bid_targets_list:
            bid_targets_list = Bid.objects.filter(istarget=True, event=event)
        bid_targets_list = list(set(bid_targets_list))  # remove duplicates
        new_donation_bids = []
        bids_affected = set()
        for donation in donations:
            if len(bid_targets_list) == 1:
                num = 1
            else:
                # weights hinted from SGDQ2020
                num = rand.choices(
                    [0, 1, 2, 3], [0 if always_assign_bids else 102, 229, 6, 1]
                )[0]

            bids = rand.sample(bid_targets_list, min(num, len(bid_targets_list)))
            new_donation_bids += list(
                DonationBid(donation=donation, bid=bid, amount=donation.amount / num)
                for bid in bids
            )
            bids_affected.update(bids)
        DonationBid.objects.bulk_create(new_donation_bids)
        for bid in bids_affected:
            # bulk_create doesn't trigger save so update the totals manually
            bid.save()
    return donations


def generate_milestone(
    rand: random.Random, event, *, amount=None, min_amount=None, max_amount=None
):
    if min_amount is None:
        min_amount = 1
    if max_amount is None:
        max_amount = 1000
    if amount is None:
        amount = random_amount(rand, min_amount=min_amount, max_amount=max_amount)
    # TODO: this very occasionally makes a duplicate
    milestone = Milestone(
        event=event,
        amount=amount,
        name=random_name(rand, 'milestone'),
        description=random_name(rand, 'description'),
        short_description=random_name(rand, 'short description'),
    )
    milestone.full_clean()
    return milestone


def generate_ad(
    rand: random.Random, *, event=None, run=None, order=None, suborder=None
):
    if event is None:
        if run:
            event = run.event
        else:
            event = rand.choice(Event.objects.all())
            assert event is not None, 'need at least one event'
    if order is None and run is None:
        run = rand.choice(event.speedrun_set.exclude(order=None))
        assert run, 'need at least one ordered run in the event'
    if suborder is None:
        last = Interstitial.objects.filter(order=order if order else run.order).last()
        suborder = last.suborder + 1 if last else 1
    ad = Ad(event=event, suborder=suborder, ad_type='IMAGE')
    if run:
        ad.anchor = run
        ad.order = run.order
    else:
        ad.order = order
    ad.filename = random_name(rand, 'filename') + '.jpg'
    ad.ad_name = random_name(rand, 'ad_name')
    ad.sponsor_name = random_name(rand, 'sponsor')
    ad.full_clean()
    return ad


def generate_interview(
    rand: random.Random, *, event=None, anchor=None, run=None, order=None, suborder=None
):
    if event is None:
        if anchor:
            event = anchor.event
        elif run:
            event = run.event
        else:
            event = rand.choice(Event.objects.all())
            assert event is not None, 'need at least one event'
    if anchor is None:
        if order is None:
            if run is None:
                run = rand.choice(event.speedrun_set.exclude(order=None))
                assert run, 'need at least one ordered run in the event'
            assert run.order is not None, 'provided run needs to be ordered'
            assert run.event == event, 'provided run needs to belong to provided event'
            order = run.order
    else:
        assert anchor.order is not None, 'provided anchor needs to be ordered'
        assert (
            anchor.event == event
        ), 'provided anchor needs to belong to provided event'
        run = anchor
        order = anchor.order
    assert order is not None, 'provide either an anchor, a run, or an order'
    if suborder is None:
        last = Interstitial.objects.for_run(run).last()
        suborder = last.suborder + 1 if last else 1
    interview = Interview(event=event, anchor=anchor, order=order, suborder=suborder)
    interview.topic = random_name(rand, 'topic')
    interview.full_clean(
        exclude='interviewers'
    )  # can't set this until we've been saved
    return interview


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
        start_time = datetime.datetime.combine(event.date, utcnow().timetz())
    event.save()

    list_of_runs = generate_runs(rand, event=event, num_runs=num_runs, ordered=True)
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
