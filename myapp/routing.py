from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from myapp import consumers

websocket_urlpatterns = [
    re_path(r'ws/device_status/$', consumers.DeviceStatusConsumer.as_asgi()),
    # Add other websocket paths here
]

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
