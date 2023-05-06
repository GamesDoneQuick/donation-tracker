from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from tracker.api.serializers import DonationProcessActionSerializer, DonationSerializer
from tracker.models import Donation, DonationProcessAction

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
        await self.send_json({'type': 'processing_action', **payload})

    async def donation_received(self, event):
        payload = event['payload']
        await self.send_json({'type': 'donation_received', **payload})

    async def donation_updated(self, event):
        payload = event['payload']
        await self.send_json({'type': 'donation_updated', **payload})


User = get_user_model()


def _serialize_donation(donation: Donation):
    return DonationSerializer(
        donation, with_permissions=('tracker.change_donation',)
    ).data


def _serialize_action(action: DonationProcessAction):
    return DonationProcessActionSerializer(action).data


def broadcast_processing_action(donation: Donation, action: DonationProcessAction):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'processing_action',
            'payload': {
                'action': _serialize_action(action),
                'donation': _serialize_donation(donation),
            },
        },
    )


def broadcast_donation_update_to_processors(donation: Donation):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'donation_updated',
            'payload': {
                'donation': _serialize_donation(donation),
            },
        },
    )


def broadcast_new_donation_to_processors(donation: Donation):
    async_to_sync(get_channel_layer().group_send)(
        PROCESSING_GROUP_NAME,
        {
            'type': 'donation_received',
            'payload': {
                'donation': _serialize_donation(donation),
            },
        },
    )
