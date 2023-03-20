from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from tracker.api.serializers import DonationSerializer
from tracker.models import Donation

PROCESSING_GROUP_NAME = 'processing'


class ProcessingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.has_perm('tracker.change_donation'):
            await self.close()
            return

        await self.channel_layer.group_add(PROCESSING_GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(PROCESSING_GROUP_NAME, self.channel_name)

    async def processing_action(self, event):
        payload = event['payload']
        await self.send_json(payload)


User = get_user_model()


def broadcast_processing_action(user: User, donation: Donation, action: str):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'processing_action',
            'payload': {
                'actor_name': user.username,
                'actor_id': user.pk,
                'donation': DonationSerializer(donation).data,
                'action': action,
            },
        },
    )
