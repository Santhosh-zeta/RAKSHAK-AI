from rest_framework import serializers
from .models import LogisticsCompany, ControlAreaContact, Truck, Trip, GPSLog, Alert


class ControlAreaContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlAreaContact
        fields = '__all__'
        read_only_fields = ['contact_id', 'created_at']


class LogisticsCompanySerializer(serializers.ModelSerializer):
    contacts       = ControlAreaContactSerializer(many=True, read_only=True)
    active_trucks  = serializers.ReadOnlyField()
    active_trips   = serializers.ReadOnlyField()

    class Meta:
        model  = LogisticsCompany
        fields = '__all__'
        read_only_fields = ['company_id', 'joined_date', 'created_at', 'updated_at']


class TruckSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Truck
        fields = '__all__'
        read_only_fields = ['truck_id', 'created_at', 'updated_at']

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Trip
        fields = '__all__'
        read_only_fields = ['trip_id']

    def validate_baseline_route_risk(self, value):
        if not (0.0 <= value <= 100.0):
            raise serializers.ValidationError("Risk must be between 0 and 100.")
        return value

    def validate_current_calculated_risk(self, value):
        if not (0.0 <= value <= 100.0):
            raise serializers.ValidationError("Risk must be between 0 and 100.")
        return value


class GPSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GPSLog
        fields = '__all__'
        read_only_fields = ['log_id', 'timestamp']

    def validate_latitude(self, value):
        if not (-90.0 <= value <= 90.0):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not (-180.0 <= value <= 180.0):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate_speed_kmh(self, value):
        if not (0.0 <= value <= 160.0):
            raise serializers.ValidationError("Speed must be between 0 and 160 km/h.")
        return value

    def validate_heading(self, value):
        if not (0.0 <= value <= 360.0):
            raise serializers.ValidationError("Heading must be between 0 and 360 degrees.")
        return value


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Alert
        fields = '__all__'
        read_only_fields = ['alert_id', 'timestamp', 'email_sent', 'sms_sent', 'notified_at']

    def validate_risk_score(self, value):
        if not (0.0 <= value <= 100.0):
            raise serializers.ValidationError("Risk score must be between 0 and 100.")
        return value
