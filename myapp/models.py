from django.db import models
from django.utils import timezone

class Prediction(models.Model):
    device_id = models.CharField(max_length=100, default='unknown_device')
    label = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} - {self.label} @ {self.timestamp}"

class Location(models.Model):
    device_id = models.CharField(max_length=100, default='unknown_device')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} @ {self.timestamp}"

class DeviceIP(models.Model):
    device_id = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} - {self.ip_address} @ {self.timestamp}"

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.username} Profile"

class DeviceStatus(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10)  # "ONLINE" or "OFFLINE"
    mode = models.CharField(max_length=10)    # "MOVING", "IDLE", "UNKNOWN"
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.device_id}: {self.status}, {self.mode} @ {self.last_active}"