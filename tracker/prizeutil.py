import datetime
import pytz
import random
import logging

from django.db import transaction

from . import util
from tracker.models import PrizeKey, PrizeWinner

logger = logging.getLogger(__name__)


@transaction.atomic()
def draw_prize(prize, seed=None, rand=None):
    try:
        rand = rand or random.Random(seed)
    except TypeError as e:
        return False, {'error': 'Seed parameter was unhashable', 'exc': e}
    if prize.key_code:
        return draw_keys(prize, seed, rand)
    eligible = prize.eligible_donors()
    if prize.maxed_winners():
        if prize.maxwinners == 1:
            return False, {'error': 'Prize: ' + prize.name + ' already has a winner.'}
        else:
            return (
                False,
                {
                    'error': 'Prize: '
                    + prize.name
                    + ' already has the maximum number of winners allowed.'
                },
            )
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=prize.event.prize_accept_deadline_delta)
    accept_deadline = (
        today.replace(tzinfo=util.anywhere_on_earth_tz(), hour=23, minute=59, second=59)
        + delta
    )
    if not eligible:
        return False, {'error': 'Prize: ' + prize.name + ' has no eligible donors.'}
    prize.get_expired_winners().update(declinecount=1, pendingcount=0)
    num_to_draw = prize.maxwinners - prize.current_win_count()

    if len(eligible) <= num_to_draw:
        winners = eligible
    else:
        winners = rand.sample(eligible, num_to_draw)
    try:
        PrizeWinner.objects.bulk_create(
            [
                PrizeWinner(
                    prize=prize,
                    winner_id=winner['donor'],
                    acceptdeadline=accept_deadline,
                )
                for winner in winners
            ]
        )
    except Exception as e:
        logger.exception('Could not draw prize')
        return (
            False,
            {'error': 'Error drawing prize: ' + prize.name + ', ' + str(e), 'exc': e},
        )
    return True, {'winners': [w['donor'] for w in winners]}


@transaction.atomic()
def draw_keys(prize, seed=None, rand=None):
    try:
        rand = rand or random.Random(seed)
    except TypeError as e:
        return False, {'error': 'Seed parameter was unhashable', 'exc': e}
    if not prize.key_code:
        return False, {'error': 'Attempted to draw keys for a non-key prize.'}
    eligible = prize.eligible_donors()
    if not eligible:
        return False, {'error': 'Prize: ' + prize.name + ' has no eligible donors.'}
    unclaimed_keys = (
        PrizeKey.objects.select_for_update()
        .filter(prize=prize, prize_winner_id=None)
        .order_by()
    )
    if len(eligible) <= unclaimed_keys.count():
        winners = eligible
    else:
        winners = rand.sample(eligible, unclaimed_keys.count())
    for key, winner in zip(unclaimed_keys, winners):
        key.prize_winner = PrizeWinner.objects.create(
            prize=prize,
            winner_id=winner['donor'],
            pendingcount=0,
            acceptcount=1,
            emailsent=True,
            acceptemailsentcount=1,
            shippingstate='SHIPPED',
        )
        key.save()
    return True, {'winners': [w['donor'] for w in winners]}


def get_past_due_prize_winners(event):
    now = datetime.datetime.utcnow().astimezone(pytz.utc)
    return PrizeWinner.objects.filter(acceptdeadline__lte=now, pendingcount__gte=1)
