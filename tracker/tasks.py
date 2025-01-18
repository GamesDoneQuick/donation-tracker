from asgiref.sync import async_to_sync
from celery import shared_task
from celery.utils.log import get_task_logger
from channels.layers import get_channel_layer

logger = get_task_logger(__name__)


@shared_task
def post_donation_to_postbacks(donation_id):
    from . import eventutil, models

    donation = models.Donation.objects.prefetch_related('bids', 'bids__bid').get(
        pk=donation_id
    )
    eventutil.post_donation_to_postbacks(donation)


@shared_task
def celery_test():
    from . import util

    async_to_sync(get_channel_layer().group_send)(
        'celery',
        {
            'type': 'pong',
            'timestamp': util.utcnow().isoformat(),
        },
    )


@shared_task(bind=True, max_retries=0)
def draw_prize(self, prize_or_pk):
    from . import models, prizeutil

    if isinstance(prize_or_pk, models.Prize):
        prize = prize_or_pk
    else:
        prize = models.Prize.objects.get(pk=prize_or_pk)

    drawn, msg = prizeutil.draw_prize(prize)
    if drawn:
        logger.info(f'Drew {len(msg["winners"])} winner(s) for Prize #{prize.pk}')
    else:
        logger.error(f'Could not draw winner(s) for Prize #{prize.pk}: {msg["error"]}')
        if self.request.id:
            raise ValueError(msg['error']) from msg.get('exc', None)
    return drawn, msg
