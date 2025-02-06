import msgpack
from channels.layers import InMemoryChannelLayer


class MsgPackLayer(InMemoryChannelLayer):
    async def group_send(self, group, message):
        await super().group_send(group, message)
        # to ensure it works with redis
        assert msgpack.unpackb(msgpack.packb(message)) == message
