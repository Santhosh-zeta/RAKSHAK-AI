from django.db import models
import uuid

class Truck(models.Model):
    truck_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver_name = models.CharField(max_length=255)
    driver_phone = models.CharField(max_length=50, blank=True, null=True)
    license_plate = models.CharField(max_length=50, unique=True, null=True)
    cargo_type = models.CharField(max_length=255)
    cargo_value = models.DecimalField(max_digits=12, decimal_places=2)
    iot_sensor_id = models.CharField(max_length=100, blank=True, null=True)
    vehicle_make_model = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.license_plate or 'Unknown'} - {self.driver_name}"

class Trip(models.Model):
    trip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='trips')
    start_location_name = models.CharField(max_length=255)
    start_location_coords = models.CharField(max_length=255, blank=True, null=True)
    destination_name = models.CharField(max_length=255)
    destination_coords = models.CharField(max_length=255, blank=True, null=True)
    start_time = models.DateTimeField()
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    
    baseline_route_risk = models.FloatField(default=0.0)
    current_calculated_risk = models.FloatField(default=0.0)
    
    status_choices = [
        ('Scheduled', 'Scheduled'),
        ('In-Transit', 'In-Transit'),
        ('Completed', 'Completed'),
        ('Alert', 'Alert'),
        ('Cancelled', 'Cancelled')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='Scheduled')

    def __str__(self):
        return f"Trip {self.trip_id} from {self.start_location_name} to {self.destination_name}"

class GPSLog(models.Model):
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='gps_logs')
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_kmh = models.FloatField(default=0.0)
    heading = models.FloatField(default=0.0)
    engine_status = models.BooleanField(default=True)
    door_sealed = models.BooleanField(default=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for Trip {self.trip.trip_id} at {self.timestamp}"

class Alert(models.Model):
    alert_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='alerts')
    
    alert_types = [
        ('Vision', 'Vision Detection'),
        ('Behavior', 'Suspicious Behavior'),
        ('Route', 'Route Deviation'),
        ('System', 'System Alert'),
        ('Fusion', 'High Risk Fusion Alert'),
        ('IoT', 'IoT Sensor Anomaly')
    ]
    type = models.CharField(max_length=20, choices=alert_types)
    
    severity_choices = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical')
    ]
    severity = models.CharField(max_length=20, choices=severity_choices, default='Medium')
    
    risk_score = models.FloatField()
    description = models.TextField()
    ai_explanation = models.TextField(blank=True, null=True)
    resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity}] {self.type} Alert ({self.risk_score}) for Trip {self.trip.trip_id}"
