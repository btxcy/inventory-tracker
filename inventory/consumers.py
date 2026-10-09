# web socket view

import json

from channels.generic.websocket import AsyncWebsocketConsumer

class StockConsumer(AsyncWebsocketConsumer):
    group_name = "stock"

    async def connect(self):
        # check if user if authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def stock_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))