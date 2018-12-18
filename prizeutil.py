import datetime
import pytz
import random

from django.db import transaction

from . import util
from .models import *


@transaction.atomic()
def draw_prize(prize, seed=None, rand=None):
    try:
        rand = rand or random.Random(seed)
    except TypeError:
        return False, {'error': 'Seed parameter was unhashable'}
    if prize.key_code:
        return False, {'error': 'Key code prizes cannot be drawn with this method.'}
    eligible = prize.eligible_donors()
    if prize.maxed_winners():
        if prize.maxwinners == 1:
            return False, {"error": "Prize: " + prize.name + " already has a winner."}
        else:
            return False, {"error": "Prize: " + prize.name + " already has the maximum number of winners allowed."}
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=prize.event.prize_accept_deadline_delta)
    acceptDeadline = today.replace(tzinfo=util.anywhere_on_earth_tz(), hour=23, minute=59, second=59) + delta
    if not eligible:
        return False, {"error": "Prize: " + prize.name + " has no eligible donors."}
    # TODO: clean this up and make it real
    # elif len(prize.eligible_donors()) <= (prize.maxwinners - len(prize.get_prize_winners())):
    #     winners = PrizeWinner.objects.bulk_create(
    #         [PrizeWinner(prize=prize, winner_id=d['donor'], acceptdeadline=acceptDeadline) for d in eligible]
    #     )
    #     return True, {'winners': [w.id for w in winners]}
    else:
        psum = reduce(lambda a, b: a + b['weight'], eligible, 0.0)
        result = rand.random() * psum
        ret = {'sum': psum, 'result': result}
        for d in eligible:
            if result < d['weight']:
                try:
                    winRecord, created = PrizeWinner.objects.get_or_create(
                        prize=prize, winner_id=d['donor'], defaults=dict(acceptdeadline=acceptDeadline))
                    if not created:
                        winRecord.pendingcount += 1
                    ret['winner'] = winRecord.winner.id
                    winRecord.save()
                except Exception as e:
                    return False, {"error": "Error drawing prize: " + prize.name + ", " + str(e)}
                return True, ret
            result -= d['weight']
        return False, {"error": "Prize drawing algorithm failed."}


@transaction.atomic()
def draw_keys(prize, seed=None, rand=None):
    try:
        rand = rand or random.Random(seed)
    except TypeError:
        return False, {'error': 'Seed parameter was unhashable'}
    eligible = prize.eligible_donors()
    if not eligible:
        return False, {"error": "Prize: " + prize.name + " has no eligible donors."}
    unclaimed_keys = PrizeKey.objects.select_for_update().filter(prize=prize, prize_winner_id=None).order_by()
    if unclaimed_keys.count() >= len(eligible):
        winners = eligible
    else:
        winners = rand.sample(eligible, unclaimed_keys.count())
    for key, d in zip(unclaimed_keys, winners):
        key.prize_winner = PrizeWinner.objects.create(
            prize=prize, winner_id=d['donor'], pendingcount=0, acceptcount=1,
            emailsent=True, acceptemailsentcount=1, shippingstate='SHIPPED',
        )
        key.save()
    return True, {'winners': [w['donor'] for w in winners]}


def get_past_due_prize_winners(event):
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    return PrizeWinner.objects.filter(acceptdeadline__lte=now, pendingcount__gte=1)


def close_past_due_prize_winners(event, verbosity=0, dry_run=False):
    for prizewinner in get_past_due_prize_winners(event):
        if verbosity > 0:
            print("Closing Prize Winner #{0} with {1} pending".format(
                prizewinner.id, prizewinner.pendingcount))
        if not dry_run:
            prizewinner.declinecount += prizewinner.pendingcount
            prizewinner.pendingcount = 0
            prizewinner.save()
