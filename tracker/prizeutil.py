import datetime
import logging
import random
from typing import Hashable, Optional

from django.db import transaction

from tracker.models import Prize, PrizeClaim, PrizeKey

from . import util

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
    prize.claims.decline_expired()
    num_to_draw = prize.maxwinners - prize.current_win_count()

    if len(eligible) <= num_to_draw:
        winners = eligible
    else:
        winners = rand.sample(list(eligible), num_to_draw)
    try:
        PrizeClaim.objects.bulk_create(
            [
                PrizeClaim(
                    prize=prize,
                    winner=winner,
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
    return True, {'winners': [w.id for w in winners]}


@transaction.atomic()
def draw_keys(prize: Prize, seed: Optional[Hashable] = None, rand=None):
    try:
        rand = rand or random.Random(seed)
    except TypeError as e:
        return False, {'error': 'Seed parameter was unhashable', 'exc': e}
    if not prize.key_code:
        return False, {'error': 'Attempted to draw keys for a non-key prize.'}
    eligible = list(prize.eligible_donors())
    if not eligible:
        return False, {'error': 'Prize: ' + prize.name + ' has no eligible donors.'}
    unclaimed_keys = (
        PrizeKey.objects.select_for_update()
        .filter(prize=prize, prize_claim_id=None)
        .order_by()
    )
    if len(eligible) <= unclaimed_keys.count():
        winners = eligible
    else:
        winners = rand.sample(eligible, unclaimed_keys.count())
    for key, winner in zip(unclaimed_keys, winners):
        key.create_winner(winner)
    return True, {'winners': [w.id for w in winners]}


def get_past_due_prize_claims(event):
    now = util.utcnow()
    return PrizeClaim.objects.filter(acceptdeadline__lte=now, pendingcount__gte=1)
