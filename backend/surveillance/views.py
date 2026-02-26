from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import LogisticsCompany, ControlAreaContact, Truck, Trip, GPSLog, Alert
from .serializers import (
    LogisticsCompanySerializer, ControlAreaContactSerializer,
    TruckSerializer, TripSerializer, GPSLogSerializer, AlertSerializer,
)
from .permissions import IsCompanyUserOrAdmin, get_company_filter


# ============================================================
# Logistics Company
# ============================================================

class LogisticsCompanyViewSet(viewsets.ModelViewSet):
    """CRUD for logistics companies. Includes nested contacts and computed truck/trip counts."""
    serializer_class = LogisticsCompanySerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = LogisticsCompany.objects.prefetch_related('contacts', 'trucks').all()
        company = get_company_filter(self.request.user)
        if company:
            qs = qs.filter(company_id=company.company_id)
            
        active = self.request.query_params.get('active')
        if active is not None:
            qs = qs.filter(active=active.lower() == 'true')
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)
        return qs

    @action(detail=True, methods=['get'])
    def trucks(self, request, pk=None):
        company = self.get_object()
        trucks = company.trucks.all()
        return Response(TruckSerializer(trucks, many=True).data)

    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        company = self.get_object()
        truck_ids = company.trucks.values_list('truck_id', flat=True)
        trip_ids  = Trip.objects.filter(truck__truck_id__in=truck_ids).values_list('trip_id', flat=True)
        alerts    = Alert.objects.filter(trip__trip_id__in=trip_ids).order_by('-timestamp')[:50]
        return Response(AlertSerializer(alerts, many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        company  = self.get_object()
        trucks   = company.trucks.all()
        truck_ids = trucks.values_list('truck_id', flat=True)
        trips    = Trip.objects.filter(truck__truck_id__in=truck_ids)
        alerts   = Alert.objects.filter(trip__in=trips)

        return Response({
            "company": company.name,
            "total_trucks":   trucks.count(),
            "active_trucks":  trucks.filter(active=True).count(),
            "total_trips":    trips.count(),
            "active_trips":   trips.filter(status__in=['Scheduled', 'In-Transit']).count(),
            "alert_trips":    trips.filter(status='Alert').count(),
            "total_alerts":   alerts.count(),
            "unresolved":     alerts.filter(resolved=False).count(),
            "critical_alerts": alerts.filter(severity='Critical', resolved=False).count(),
        })


# ============================================================
# Control Area Contact
# ============================================================

class ControlAreaContactViewSet(viewsets.ModelViewSet):
    serializer_class = ControlAreaContactSerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = ControlAreaContact.objects.select_related('company').all()
        company = get_company_filter(self.request.user)
        if company:
            qs = qs.filter(company=company)
            
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(company__company_id=company_id)
        active = self.request.query_params.get('active')
        if active is not None:
            qs = qs.filter(active=active.lower() == 'true')
        return qs


# ============================================================
# Truck
# ============================================================

class TruckViewSet(viewsets.ModelViewSet):
    serializer_class = TruckSerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = Truck.objects.select_related('company').all()
        company_filter = get_company_filter(self.request.user)
        if company_filter:
            qs = qs.filter(company=company_filter)
            
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(company__company_id=company_id)
        active = self.request.query_params.get('active')
        if active is not None:
            qs = qs.filter(active=active.lower() == 'true')
        return qs


# ============================================================
# Trip
# ============================================================

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = Trip.objects.select_related('truck__company').all()
        company_filter = get_company_filter(self.request.user)
        if company_filter:
            qs = qs.filter(truck__company=company_filter)
            
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(truck__company__company_id=company_id)
        truck_id = self.request.query_params.get('truck_id')
        if truck_id:
            qs = qs.filter(truck__truck_id=truck_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        from .services.map_service import GeoSpatialService
        trip = serializer.save()
        start_coords = GeoSpatialService.get_coordinates(trip.start_location_name)
        dest_coords  = GeoSpatialService.get_coordinates(trip.destination_name)
        trip.start_location_coords = start_coords
        trip.destination_coords    = dest_coords
        route_info = GeoSpatialService.calculate_route(start_coords, dest_coords)
        distance = route_info.get("distance_meters", 100000)
        baseline_risk = GeoSpatialService.calculate_baseline_risk(
            distance, trip.start_location_name, trip.destination_name
        )
        trip.baseline_route_risk     = baseline_risk
        trip.current_calculated_risk = baseline_risk
        trip.save()

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        trip        = self.get_object()
        latest_gps  = trip.gps_logs.order_by('-timestamp').first()
        recent_alerts = trip.alerts.order_by('-timestamp')[:5]
        current_risk = min(100, sum(a.risk_score for a in recent_alerts) if recent_alerts else 0)
        return Response({
            'trip_id':           trip.trip_id,
            'status':            trip.status,
            'current_risk_score': current_risk,
            'latest_location':   GPSLogSerializer(latest_gps).data if latest_gps else None,
            'recent_alerts':     AlertSerializer(recent_alerts, many=True).data,
        })


# ============================================================
# GPS Log
# ============================================================

class GPSLogViewSet(viewsets.ModelViewSet):
    serializer_class = GPSLogSerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = GPSLog.objects.all()
        company_filter = get_company_filter(self.request.user)
        if company_filter:
            qs = qs.filter(trip__truck__company=company_filter)
            
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            qs = qs.filter(trip__trip_id=trip_id)
        return qs


# ============================================================
# Alert
# ============================================================

class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsCompanyUserOrAdmin]

    def get_queryset(self):
        qs = Alert.objects.select_related('trip__truck__company').all()
        company_filter = get_company_filter(self.request.user)
        if company_filter:
            qs = qs.filter(trip__truck__company=company_filter)
            
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            qs = qs.filter(trip__trip_id=trip_id)
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(trip__truck__company__company_id=company_id)
        severity = self.request.query_params.get('severity')
        if severity:
            qs = qs.filter(severity=severity)
        resolved = self.request.query_params.get('resolved')
        if resolved is not None:
            qs = qs.filter(resolved=resolved.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        from .notification_service import dispatch_alert
        alert = serializer.save()
        trip  = alert.trip
        truck = trip.truck
        company = truck.company

        severity_rank = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
        if severity_rank.get(alert.severity, 0) >= 2:
            try:
                dispatch_alert(alert, trip, truck, company)
                alert.email_sent  = True
                alert.sms_sent    = True
                alert.notified_at = timezone.now()
                alert.save(update_fields=['email_sent', 'sms_sent', 'notified_at'])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Notification dispatch failed: {e}")

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolved = True
        alert.save(update_fields=['resolved'])
        return Response({'status': 'resolved', 'alert_id': alert.alert_id})

    @action(detail=True, methods=['post'])
    def resend_notifications(self, request, pk=None):
        from .notification_service import dispatch_alert
        alert = self.get_object()
        trip  = alert.trip
        truck = trip.truck
        try:
            dispatch_alert(alert, trip, truck, truck.company)
            alert.notified_at = timezone.now()
            alert.save(update_fields=['notified_at'])
            return Response({'status': 'notifications_sent'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
