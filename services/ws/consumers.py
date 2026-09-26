import json
from channels.generic.websocket import AsyncWebsocketConsumer
from services import models
from asgiref.sync import sync_to_async
from django.db import transaction


class ScheduleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Conecta al grupo de WebSocket para las reservas
        self.room_group_name = 'scheduling'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Desconecta del grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Maneja las solicitudes de reserva.
        """
        try:
            data = json.loads(text_data)
            slot_id = data['slot_id']

            # Intenta reservar el slot
            success = await sync_to_async(self.reserve_slot)(slot_id)

            if success:
                # Notifica a todos los clientes conectados que el slot
                # fue reservado
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'update_slot',
                        'slot_id': slot_id,
                        'is_reserved': True,
                    }
                )
            else:
                # Notifica al cliente que la reserva falló
                await self.send(text_data=json.dumps({
                    'error': 'El slot ya ha sido reservado.',
                }))
        except Exception as e:
            # Notifica al cliente que la reserva falló
            await self.send(text_data=json.dumps({
                'error': str(e),
            }))

    async def update_slot(self, event):
        """
        Envia actualizaciones a los clientes sobre los slots reservados.
        """
        await self.send(text_data=json.dumps({
            'slot_id': event['slot_id'],
            'is_reserved': event['is_reserved'],
        }))

    def reserve_slot(self, slot_id):
        """
        Lógica de reserva del slot.
        """
        try:
            with transaction.atomic():
                slot = models.Slot.objects.select_for_update().get(id=slot_id)
                if slot.is_reserved:
                    return False
                slot.is_reserved = True
                slot.save()
                return True
        except models.Slot.DoesNotExist:
            return False
