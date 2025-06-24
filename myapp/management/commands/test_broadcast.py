from django.core.management.base import BaseCommand
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class Command(BaseCommand):
    help = 'Broadcasts a test device.status message to the device_status group.'

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        data = [{
            'device_id': 'test-device',
            'ip': '127.0.0.1',
            'status': 'ONLINE',
            'mode': 'MOVING',
            'last_active': 'NOW',
        }]
        async_to_sync(channel_layer.group_send)(
            'device_status',
            {
                'type': 'device.status',
                'data': data
            }
        )
        self.stdout.write(self.style.SUCCESS('Test device.status message sent to device_status group.'))
