from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Truck, Trip, GPSLog, Alert
from .serializers import TruckSerializer, TripSerializer, GPSLogSerializer, AlertSerializer

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    serializer_class = TruckSerializer

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    def perform_create(self, serializer):
        from .services.map_service import GeoSpatialService
        
        # 1. Save initial trip details to access names
        trip = serializer.save()
        
        # 2. Get coords
        start_coords = GeoSpatialService.get_coordinates(trip.start_location_name)
        dest_coords = GeoSpatialService.get_coordinates(trip.destination_name)
        trip.start_location_coords = start_coords
        trip.destination_coords = dest_coords
        
        # 3. Calculate distance and risk
        route_info = GeoSpatialService.calculate_route(start_coords, dest_coords)
        if route_info["success"]:
            # Optionally set estimated arrival here based on duration
            pass
            
        distance = route_info.get("distance_meters", 100000) # fallback 100km
        
        baseline_risk = GeoSpatialService.calculate_baseline_risk(
            distance, trip.start_location_name, trip.destination_name
        )
        
        trip.baseline_route_risk = baseline_risk
        trip.current_calculated_risk = baseline_risk
        trip.save()

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        trip = self.get_object()
        latest_gps = trip.gps_logs.order_by('-timestamp').first()
        recent_alerts = trip.alerts.order_by('-timestamp')[:5]
        
        # Calculate a mock risk score for now based on alerts
        current_risk = min(100, sum(alert.risk_score for alert in recent_alerts) if recent_alerts else 0)

        return Response({
            'trip_id': trip.trip_id,
            'status': trip.status,
            'current_risk_score': current_risk,
            'latest_location': GPSLogSerializer(latest_gps).data if latest_gps else None,
            'recent_alerts': AlertSerializer(recent_alerts, many=True).data
        })

class GPSLogViewSet(viewsets.ModelViewSet):
    queryset = GPSLog.objects.all()
    serializer_class = GPSLogSerializer

    def get_queryset(self):
        queryset = GPSLog.objects.all()
        trip_id = self.request.query_params.get('trip_id', None)
        if trip_id is not None:
            queryset = queryset.filter(trip__trip_id=trip_id)
        return queryset

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer

    def get_queryset(self):
        queryset = Alert.objects.all()
        trip_id = self.request.query_params.get('trip_id', None)
        if trip_id is not None:
            queryset = queryset.filter(trip__trip_id=trip_id)
        return queryset
