from rest_framework import serializers
from .models import Prediction, Location, DeviceIP

class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ['device_id', 'label', 'latitude', 'longitude', 'timestamp']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['device_id', 'latitude', 'longitude', 'timestamp']

class DeviceIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceIP
        fields = ['device_id', 'ip_address', 'timestamp']
