from rest_framework import serializers
from .models import Truck, Trip, GPSLog, Alert

class TruckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'

class GPSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSLog
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'
