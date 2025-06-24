import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import DeviceIP, Location, DeviceStatus
from .views import broadcast_device_status_update

logger = logging.getLogger(__name__)

@shared_task
def device_heartbeat_check():
    now = timezone.now()
    devices = DeviceIP.objects.values('device_id').distinct()
    status_changed = False
    logger.info(f"[Celery] device_heartbeat_check running at {now}")  # DEBUG

    for device in devices:
        device_id = device['device_id']
        last_ip = DeviceIP.objects.filter(device_id=device_id).order_by('-timestamp').first()
        last_location = Location.objects.filter(device_id=device_id).order_by('-timestamp').first()

        new_status = "ONLINE" if last_ip and (now - last_ip.timestamp <= timedelta(minutes=1)) else "OFFLINE"

        if last_location and (now - last_location.timestamp <= timedelta(minutes=1)):
            new_mode = "MOVING"
        elif last_location:
            new_mode = "IDLE"
        else:
            new_mode = "UNKNOWN"

        status_obj, created = DeviceStatus.objects.get_or_create(device_id=device_id)
        if created or status_obj.status != new_status or status_obj.mode != new_mode:
            logger.info(f"Device {device_id}: Status {status_obj.status} -> {new_status}, Mode {status_obj.mode} -> {new_mode}")
            status_obj.status = new_status
            status_obj.mode = new_mode
            status_obj.last_active = last_location.timestamp if last_location else None
            status_obj.save()
            status_changed = True

    # Always broadcast, even if no status changed
    logger.info("[Celery] Broadcasting device status update...")  # DEBUG
    broadcast_device_status_update()
