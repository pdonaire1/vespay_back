from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NFCConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"nfc_{self.session_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def payment_event(self, event: dict) -> None:
        await self.send_json({"event": event["event"], **event["payload"]})
