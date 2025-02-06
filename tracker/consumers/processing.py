import asyncio

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from tracker import util
from tracker.api.serializers import DonationSerializer
from tracker.models import Donation

# TODO: split this channel based on permissions of the connecting user
#  view donor?
#  view bid?
#  view mod comment?
PROCESSING_GROUP_NAME = 'processing'


class ProcessingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        perm = sync_to_async(self.user.has_perm)
        if not (
            all(
                await asyncio.gather(
                    perm('tracker.view_comments'),
                    perm('tracker.view_donation'),
                    perm('tracker.view_bid'),
                )
            )
        ):
            await self.close()
            return

        await self.channel_layer.group_add(PROCESSING_GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(PROCESSING_GROUP_NAME, self.channel_name)

    async def processing_action(self, event):
        payload = event['payload']
        await self.send_json({'type': 'processing_action', **payload})

    async def donation_received(self, event):
        payload = event['payload']
        await self.send_json({'type': 'donation_received', **payload})


User = get_user_model()


def _serialize_donation(donation: Donation):
    return DonationSerializer(
        donation,
        with_all_comments=True,
        with_mod_comments=True,
        with_permissions=(
            'tracker.view_comments',
            'tracker.view_donation',
            'tracker.view_bid',
        ),
    ).data


def broadcast_processing_action(user: User, donation: Donation, action: str):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'processing_action',
            'payload': {
                'actor_name': user.username,
                'actor_id': user.pk,
                'donation': _serialize_donation(donation),
                'action': action,
            },
        },
    )


def broadcast_new_donation_to_processors(
    donation: Donation, total: float, donation_count: int
):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'donation_received',
            'payload': {
                'donation': _serialize_donation(donation),
                'event_total': total,
                'donation_count': donation_count,
                'posted_at': str(util.utcnow()),
            },
        },
    )
