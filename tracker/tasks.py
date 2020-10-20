import datetime

import pytz
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.utils.log import get_task_logger
from channels.layers import get_channel_layer

from . import eventutil, prizeutil
from .models import Donation, Prize

logger = get_task_logger(__name__)


@shared_task
def post_donation_to_postbacks(donation_id):
    donation = Donation.objects.get(pk=donation_id)
    eventutil.post_donation_to_postbacks(donation)


@shared_task
def celery_test():
    async_to_sync(get_channel_layer().group_send)(
        'celery',
        {'type': 'pong', 'timestamp': datetime.datetime.now(tz=pytz.utc).isoformat(),},
    )


@shared_task(bind=True, max_retries=0)
def draw_prize(self, prize_or_pk):
    if isinstance(prize_or_pk, Prize):
        prize = prize_or_pk
    else:
        prize = Prize.objects.get(pk=prize_or_pk)
    drawn, msg = prizeutil.draw_prize(prize)
    if drawn:
        logger.info(f'Drew {len(msg["winners"])} winner(s) for Prize #{prize.pk}')
    else:
        logger.error(f'Could not draw winner(s) for Prize #{prize.pk}: {msg["error"]}')
        if self.request.id:
            raise ValueError(msg['error']) from msg.get('exc', None)
    return drawn, msg
