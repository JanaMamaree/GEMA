from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import DeviceIP, Location
from django.utils import timezone
from datetime import timedelta
import logging

def broadcast_device_status_update():
    logger = logging.getLogger(__name__)
    logger.info("[Broadcast] broadcast_device_status_update called")  # DEBUG
    devices = DeviceIP.objects.values('device_id').distinct()
    data = []
    now = timezone.now()
    for device in devices:
        device_id = device['device_id']
        last_ip = DeviceIP.objects.filter(device_id=device_id).order_by('-timestamp').first()
        last_location = Location.objects.filter(device_id=device_id).order_by('-timestamp').first()
        if last_ip and (now - last_ip.timestamp <= timedelta(minutes=1)):
            status = "ONLINE"
        else:
            status = "OFFLINE"
        if last_location and (now - last_location.timestamp <= timedelta(minutes=1)):
            mode = "MOVING"
            last_active = "NOW"
        else:
            mode = "IDLE"
            if last_location:
                last_active_time = last_location.timestamp + timedelta(hours=2)
                last_active = last_active_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_active = "N/A"
        ip_address = last_ip.ip_address if last_ip else ""
        data.append({
            "device_id": device_id,
            "ip": ip_address,
            "status": status,
            "mode": mode,
            "last_active": last_active,
        })
    logger.info(f"[Broadcast] Sending device.status to channel layer: {data}")  # DEBUG
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "device_status",
        {
            "type": "device.status",
            "data": data
        }
    )
