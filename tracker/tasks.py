import datetime

import pytz
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from . import eventutil
from .models import Donation


@shared_task
def post_donation_to_postbacks(donation_id):
    donation = Donation.objects.get(pk=donation_id)
    eventutil.post_donation_to_postbacks(donation)


@shared_task
def celery_test():
    async_to_sync(get_channel_layer().group_send)(
        'celery',
        {
            'type': 'completion',
            'timestamp': datetime.datetime.now(tz=pytz.utc).isoformat(),
        },
    )
