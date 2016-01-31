import datetime
import pytz
import random

from tracker.models import *
import tracker.util as util

def draw_prize(prize, seed=None):
    eligible = prize.eligible_donors()
    if prize.maxed_winners():
        if prize.maxwinners == 1:
            return False, {"error": "Prize: " + prize.name + " already has a winner."}
        else:
            return False, {"error": "Prize: " + prize.name + " already has the maximum number of winners allowed."}
    if not eligible:
        return False, {"error": "Prize: " + prize.name + " has no eligible donors."}
    else:
        rand = None
        try:
            rand = random.Random(seed)
        except TypeError:  # not sure how this could happen but hey
            return False, {'error': 'Seed parameter was unhashable'}
        psum = reduce(lambda a, b: a + b['weight'], eligible, 0.0)
        result = rand.random() * psum
        ret = {'sum': psum, 'result': result}
        for d in eligible:
            if result < d['weight']:
                try:
                    donor = Donor.objects.get(pk=d['donor'])
                    acceptDeadline = datetime.datetime.today().replace(tzinfo=util.anywhere_on_earth_tz(), hour=23,
                                                                       minute=59, second=59) + datetime.timedelta(days=prize.event.prize_accept_deadline_delta)
                    winRecord, created = PrizeWinner.objects.get_or_create(
                        prize=prize, winner=donor, acceptdeadline=acceptDeadline)
                    if not created:
                        winRecord.pendingcount += 1
                    ret['winner'] = winRecord.winner.id
                    winRecord.save()
                except Exception as e:
                    return False, {"error": "Error drawing prize: " + prize.name + ", " + str(e)}
                return True, ret
            result -= d['weight']
        return False, {"error": "Prize drawing algorithm failed."}


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
