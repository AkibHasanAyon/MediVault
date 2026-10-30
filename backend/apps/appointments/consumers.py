import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from channels.db import database_sync_to_async

logger = logging.getLogger('medivault.appointments.queue')


class ClinicQueueConsumer(AsyncWebsocketConsumer):
    """
    Real-Time Chamber Queue WebSocket Consumer.
    Listens to clinic-wide and doctor-specific queue events:
    - TOKEN_ISSUED
    - PATIENT_CALLED
    - CONSULTATION_STARTED
    - CONSULTATION_ENDED
    - PATIENT_SKIPPED
    - QUEUE_SYNC
    """
    async def connect(self):
        self.clinic_id = self.scope['url_route']['kwargs'].get('clinic_id')
        self.doctor_id = self.scope['url_route']['kwargs'].get('doctor_id')
        self.user = self.scope.get('user')

        if not self.clinic_id:
            await self.close(code=4000)
            return

        self.clinic_group_name = f"queue_clinic_{self.clinic_id}"
        self.doctor_group_name = f"queue_doctor_{self.doctor_id}" if self.doctor_id else None

        # Add to clinic room group
        await self.channel_layer.group_add(
            self.clinic_group_name,
            self.channel_name
        )

        # Add to doctor chamber room group if specified
        if self.doctor_group_name:
            await self.channel_layer.group_add(
                self.doctor_group_name,
                self.channel_name
            )

        await self.accept()

        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "clinic_id": str(self.clinic_id),
            "doctor_id": str(self.doctor_id) if self.doctor_id else None,
            "authenticated": bool(self.user and self.user.is_authenticated),
            "timestamp": timezone.now().isoformat(),
        }))

    async def disconnect(self, close_code):
        # Leave clinic room group
        if hasattr(self, 'clinic_group_name'):
            await self.channel_layer.group_discard(
                self.clinic_group_name,
                self.channel_name
            )
        # Leave doctor chamber group
        if hasattr(self, 'doctor_group_name') and self.doctor_group_name:
            await self.channel_layer.group_discard(
                self.doctor_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
            return

        action = data.get('action')

        if action == 'ping':
            await self.send(text_data=json.dumps({"type": "PONG", "timestamp": timezone.now().isoformat()}))
        
        elif action == 'subscribe_doctor':
            doctor_id = data.get('doctor_id')
            if doctor_id:
                new_group = f"queue_doctor_{doctor_id}"
                await self.channel_layer.group_add(new_group, self.channel_name)
                await self.send(text_data=json.dumps({
                    "type": "SUBSCRIBED_DOCTOR",
                    "doctor_id": str(doctor_id)
                }))

        elif action == 'get_queue_snapshot':
            snapshot = await self.fetch_queue_snapshot(self.clinic_id, self.doctor_id)
            await self.send(text_data=json.dumps({
                "type": "QUEUE_SNAPSHOT",
                "clinic_id": str(self.clinic_id),
                "data": snapshot
            }))

    async def queue_update(self, event):
        """
        Handler for channel layer broadcasts matching Implementation.md § 8.1.
        Forwards event payload to WebSocket client.
        """
        payload = event.get('payload', event)
        await self.send(text_data=json.dumps(payload))

    async def queue_event(self, event):
        """Generic alias for queue_update."""
        payload = event.get('payload', event)
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def fetch_queue_snapshot(self, clinic_id, doctor_id=None):
        from apps.appointments.models import QueueEntry
        today = timezone.localdate()
        qs = QueueEntry.objects.filter(clinic_id=clinic_id, queue_date=today)
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        entries = qs.order_by('token_number').select_related('patient__user', 'doctor__user')
        results = []
        for entry in entries:
            results.append({
                "id": str(entry.id),
                "token_number": entry.token_number,
                "token_display": entry.token_display,
                "state": entry.state,
                "estimated_wait_minutes": entry.estimated_wait_minutes,
                "doctor_id": str(entry.doctor_id),
                "doctor_name": entry.doctor.user.full_name,
                "patient_id": str(entry.patient_id),
                "patient_name": entry.patient.user.full_name,
                "called_at": entry.called_at.isoformat() if entry.called_at else None,
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
            })
        return results


async def async_broadcast_queue_event(clinic_id, event_type: str, data: dict, doctor_id=None):
    """
    Asynchronous utility function to broadcast queue events across Redis Channel Layer.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channel layer not configured. Skipping queue broadcast: %s", event_type)
        return

    payload = {
        "event": event_type,
        "clinic_id": str(clinic_id),
        "doctor_id": str(doctor_id) if doctor_id else None,
        "timestamp": timezone.now().isoformat(),
        "data": data,
    }

    message = {
        "type": "queue_update",
        "payload": payload,
    }

    clinic_group = f"queue_clinic_{clinic_id}"
    try:
        await channel_layer.group_send(clinic_group, message)
        if doctor_id:
            await channel_layer.group_send(f"queue_doctor_{doctor_id}", message)
        logger.info("Async broadcasted '%s' event to group %s", event_type, clinic_group)
    except Exception as e:
        logger.error("Failed to async broadcast queue event: %s", str(e))


def broadcast_queue_event(clinic_id, event_type: str, data: dict, doctor_id=None):
    """
    Synchronous utility function to broadcast queue events across Redis Channel Layer
    to all active WebSockets subscribed to clinic or doctor chamber.
    Detects whether an asyncio event loop is already running in the current thread.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channel layer not configured. Skipping queue broadcast: %s", event_type)
        return

    payload = {
        "event": event_type,
        "clinic_id": str(clinic_id),
        "doctor_id": str(doctor_id) if doctor_id else None,
        "timestamp": timezone.now().isoformat(),
        "data": data,
    }

    message = {
        "type": "queue_update",
        "payload": payload,
    }

    clinic_group = f"queue_clinic_{clinic_id}"
    try:
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If an async loop is already running in current thread (e.g. inside an async test or consumer)
            loop.create_task(channel_layer.group_send(clinic_group, message))
            if doctor_id:
                loop.create_task(channel_layer.group_send(f"queue_doctor_{doctor_id}", message))
        else:
            async_to_sync(channel_layer.group_send)(clinic_group, message)
            if doctor_id:
                async_to_sync(channel_layer.group_send)(f"queue_doctor_{doctor_id}", message)
        logger.info("Broadcasted '%s' event to group %s", event_type, clinic_group)
    except Exception as e:
        logger.error("Failed to broadcast queue event: %s", str(e))
