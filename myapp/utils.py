from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import DeviceIP, Location
from django.utils import timezone
import datetime

def send_device_updates():
    channel_layer = get_channel_layer()
    
    # Query devices + related status, mode, last active (adjust as needed)
    devices = []
    now = timezone.now()
    from django.utils.timesince import timesince
    
    # Example: loop through DeviceIPs
    for device in DeviceIP.objects.all():
        # Determine status
        status = "ONLINE" if now - device.timestamp <= datetime.timedelta(minutes=1) else "OFFLINE"
        
        # Get last location timestamp for the device
        last_location = Location.objects.filter(device_id=device.device_id).order_by('-timestamp').first()
        if last_location:
            mode = "MOVING" if (now - last_location.timestamp) <= datetime.timedelta(minutes=1) else "IDLE"
            last_active = "NOW" if mode == "MOVING" else timesince(last_location.timestamp) + " ago"
        else:
            mode = "UNKNOWN"
            last_active = "No data"
        
        devices.append({
            "device_id": device.device_id,
            "status": status,
            "mode": mode,
            "last_active": last_active,
        })
    
    async_to_sync(channel_layer.group_send)(
        "devices_group",
        {
            "type": "device_update",
            "data": devices
        }
    )
