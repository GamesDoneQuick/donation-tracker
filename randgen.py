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


def random_paypal_email(rand, base, otherEmail):
    result = otherEmail
    while result == otherEmail:
        result = random_name(rand, base) + '@gmail.com'


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


def random_amount(
    rand, rounded=True, minAmount=Decimal('0.00'), maxAmount=Decimal('10000.00')
):
    drange = maxAmount - minAmount
    return (minAmount + (drange * Decimal(rand.random()))).quantize(
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


def generate_donor(rand, firstname=None, lastname=None, alias=None, visibility=None):
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
    rand, event=None, maxRunLength=_DEFAULT_MAX_RUN_LENGTH, maxSetupLength=600
):
    run = SpeedRun()
    run.name = random_game_name(rand)
    run.description = random_game_description(rand, run.name)
    run.run_time = str(rand.randrange(60, maxRunLength))
    run.setup_time = str(rand.randrange(60, maxSetupLength))
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
        twitter=twitter or random_name(rand, 'twitter'),
        youtube=youtube or random_name(rand, 'youtube'),
        donor=donor,
    )
    runner.clean()
    return runner


def generate_prize(
    rand,
    category=None,
    event=None,
    startRun=None,
    endRun=None,
    startTime=None,
    endTime=None,
    sumDonations=None,
    minAmount=Decimal('1.00'),
    maxAmount=Decimal('20.00'),
    randomDraw=True,
    maxwinners=1,
    state='ACCEPTED',
):
    prize = Prize()
    prize.name = random_prize_name(rand)
    prize.description = random_prize_description(rand, prize.name)
    if startRun:
        prize.startrun = startRun
        prize.endrun = endRun
    elif startTime:
        prize.starttime = startTime
        prize.endtime = endTime
    if category:
        prize.category = category
    else:
        prize.category = pick_random_instance(rand, PrizeCategory)
    if true_false_or_random(rand, sumDonations):
        prize.sumdonations = True
        valA = random_amount(rand, minAmount=minAmount, maxAmount=maxAmount)
        valB = random_amount(rand, minAmount=minAmount, maxAmount=maxAmount)
        prize.minimumbid = min(valA, valB)
        prize.maximumbid = max(valA, valB)
    else:
        prize.sumdonations = False
        prize.minimumbid = prize.maximumbid = random_amount(
            rand, minAmount=minAmount, maxAmount=maxAmount
        )
    prize.randomdraw = randomDraw
    if startRun is not None:
        prize.event = startRun.event
    elif event:
        prize.event = event
    else:
        prize.event = pick_random_instance(rand, Event)
    prize.maxwinners = rand.randrange(maxwinners) + 1
    if state:
        prize.state = state
    prize.clean()
    return prize


def generate_prize_key(rand, prize=None, key=None, prize_winner=None, winner=None):
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


def generate_bid(
    rand,
    allowChildren=None,
    minChildren=2,
    maxChildren=5,
    maxDepth=2,
    addGoal=None,
    minGoal=Decimal('0.01'),
    maxGoal=Decimal('1000.00'),
    run=None,
    event=None,
    parent=None,
    state=None,
):
    bid = Bid()
    bid.description = random_bid_description(rand, bid.name)
    if true_false_or_random(rand, addGoal):
        bid.goal = random_amount(rand, minAmount=minGoal, maxAmount=maxGoal)
    children = []
    if maxDepth > 0 and true_false_or_random(rand, allowChildren):
        numChildren = rand.randint(minChildren, maxChildren)
        for c in range(0, numChildren):
            children.append(
                generate_bid(
                    rand,
                    allowChildren=False,
                    maxDepth=maxDepth - 1,
                    addGoal=addGoal,
                    minGoal=minGoal,
                    maxGoal=maxGoal,
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
        raise Exception('Fuck off')
    if parent:
        bid.parent = parent
    if run:
        bid.speedrun = run
    if event:
        bid.event = event
    if state:
        bid.state = state
    else:
        bid.state = pick_random_element(rand, Bid._meta.get_field('state').choices)[0]
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
    donor=None,
    domain=None,
    event=None,
    minAmount=Decimal('0.01'),
    maxAmount=Decimal('1000.00'),
    minTime=None,
    maxTime=None,
    donors=None,
    transactionstate=None,
):
    donation = Donation()
    donation.amount = random_amount(rand, minAmount=minAmount, maxAmount=maxAmount)
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
    if not minTime:
        minTime = event.datetime
    if not maxTime:
        maxTime = minTime + datetime.timedelta(seconds=60 * 60 * 24 * 14)
    donation.timereceived = random_time(rand, minTime, maxTime)
    donation.currency = 'USD'
    donation.transactionstate = transactionstate or 'COMPLETED'
    if donation.domain == 'LOCAL':
        assert donation.transactionstate == 'COMPLETED'

    if not donor:
        if donors:
            donor = pick_random_element(rand, donors)
        else:
            donor = pick_random_instance(rand, Donor)
    if not donor:  # no provided donors at all
        donor = generate_donor(rand)
        donor.save()
    donation.donor = donor
    donation.clean()
    return donation


def generate_donation_for_prize(rand, prize, **kwargs):
    event = kwargs.pop('event', prize.event)
    return generate_donation(
        rand,
        minAmount=prize.minimumbid,
        minTime=prize.start_draw_time(),
        maxTime=prize.end_draw_time(),
        event=event,
        **kwargs,
    )


def generate_event(rand, startTime=None):
    event = Event()
    if not startTime:
        startTime = datetime.datetime.utcnow().astimezone(pytz.utc)
    event.datetime = startTime
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


def assign_bids(rand, donation, from_set):
    remaining_amount = random_amount(rand, maxAmount=donation.amount)
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
                rand, minAmount=Decimal('1.00'), maxAmount=remaining_amount
            )
        remaining_amount = remaining_amount - use_amount
        bid = rand.choice(list(available_set))
        available_set.remove(bid)
        donation_bid = DonationBid.objects.create(
            donation=donation, bid=bid, amount=use_amount
        )
        donation_bid.clean()


def generate_runs(rand, event, numRuns, scheduled=False):
    listOfRuns = []
    lastRun = event.speedrun_set.last()
    order = lastRun.order if (lastRun and lastRun.order) else 0
    for i in range(0, numRuns):
        run = generate_run(rand, event=event)
        if scheduled:
            order = run.order = order + 1
        run.save()
        listOfRuns.append(run)
    return listOfRuns


def generate_runners(rand, numRunners):
    def save_runner(rand):
        runner = generate_runner(rand)
        runner.save()
        return runner

    return [save_runner(rand) for _ in range(numRunners)]


def generate_donors(rand, numDonors):
    listOfDonors = []
    for i in range(0, numDonors):
        donor = generate_donor(rand)
        donor.save()
        listOfDonors.append(donor)
    return listOfDonors


def generate_bids(rand, event, numBids, listOfRuns=None):
    topBidsList = []
    bidTargetsList = []

    if not listOfRuns:
        listOfRuns = list(SpeedRun.objects.filter(event=event))

    for i in range(0, numBids):
        if rand.getrandbits(2) <= 2:
            bid, children = generate_bid(
                rand, run=pick_random_element(rand, listOfRuns)
            )
        else:
            bid, children = generate_bid(rand, event=event)
        chain_insert_bid(bid, children)
        topBidsList.append(bid)
        bidTargetsList.extend(get_bid_targets(bid, children))
    return topBidsList, bidTargetsList


def generate_prizes(rand, event, numPrizes, listOfRuns=None, maxwinners=1):
    listOfPrizes = []
    if not listOfRuns:
        listOfRuns = list(SpeedRun.objects.filter(event=event))
    if not listOfRuns:
        return listOfPrizes
    numRuns = len(listOfRuns)
    startTime = listOfRuns[0].starttime
    endTime = listOfRuns[-1].endtime
    for i in range(0, numPrizes):
        if rand.getrandbits(2) <= 2:
            distance = rand.randrange(min(6, numRuns))
            startRunId = rand.randrange(numRuns - distance)
            endRunId = startRunId + distance
            prize = generate_prize(
                rand,
                event=event,
                startRun=listOfRuns[startRunId],
                endRun=listOfRuns[endRunId],
                maxwinners=maxwinners,
            )
        else:
            time0 = random_time(rand, startTime, endTime)
            time1 = random_time(rand, startTime, endTime)
            start = min(time0, time1)
            end = max(time0, time1)
            prize = generate_prize(
                rand, event=event, startTime=start, endTime=end, maxwinners=maxwinners
            )
        prize.save()
        listOfPrizes.append(prize)
    return listOfPrizes


def generate_donations(
    rand,
    event,
    numDonations,
    startTime=None,
    endTime=None,
    donors=None,
    assignBids=True,
    bidTargetsList=None,
    domain=None,
    transactionstate=None,
):
    listOfDonations = []
    if not startTime:
        startTime = event.datetime
    if not endTime:
        run = SpeedRun.objects.filter(event=event).last()
        if not run:
            raise Exception(
                'Need at least one scheduled run with a duration to generate random donations'
            )
        endTime = run.endtime
    if not bidTargetsList:
        bidTargetsList = Bid.objects.filter(istarget=True, event=event)
    for i in range(0, numDonations):
        donation = generate_donation(
            rand,
            event=event,
            minTime=startTime,
            maxTime=endTime,
            donors=donors,
            domain=domain,
            transactionstate=transactionstate,
        )
        donation.save()
        if assignBids:
            assign_bids(rand, donation, bidTargetsList)
        listOfDonations.append(donation)
    return listOfDonations


def build_random_event(
    rand, startTime=None, numDonors=0, numDonations=0, numRuns=0, numBids=0, numPrizes=0
):
    if not PrizeCategory.objects.all().exists() and numPrizes > 0:
        PrizeCategory.objects.create(name='Game')
        PrizeCategory.objects.create(name='Grand')
        PrizeCategory.objects.create(name='Grab Bag')

    event = generate_event(rand, startTime=startTime)
    if not startTime:
        startTime = datetime.datetime.combine(event.date, datetime.time()).replace(
            tzinfo=pytz.utc
        )
    event.save()

    listOfRuns = generate_runs(rand, event=event, numRuns=numRuns, scheduled=True)
    lastRunTime = listOfRuns[-1].endtime if listOfRuns else startTime
    listOfDonors = generate_donors(rand, numDonors=numDonors)
    topBidsList, bidTargetsList = generate_bids(
        rand, event=event, numBids=numBids, listOfRuns=listOfRuns
    )
    generate_prizes(rand, event=event, numPrizes=numPrizes, listOfRuns=listOfRuns)
    generate_donations(
        rand,
        event=event,
        numDonations=numDonations,
        startTime=startTime,
        endTime=lastRunTime,
        donors=listOfDonors,
        assignBids=True,
        bidTargetsList=bidTargetsList,
    )

    return event
