from rest_framework import views, status
from rest_framework.response import Response
from .models import Trip, Alert
from .serializers import AlertSerializer
import datetime

class VisionEventView(views.APIView):
    """
    Endpoint for the Perception Agent to report raw CV detections 
    (e.g., "Person detected near door"). Creates an alert if rules are met.
    """
    def post(self, request):
        trip_id = request.data.get('trip_id')
        event_type = request.data.get('event_type') # e.g. "Person Detected"
        confidence = request.data.get('confidence', 0.0)
        
        if not trip_id or not event_type:
            return Response({"error": "trip_id and event_type are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Baseline rule: high confidence detection = Alert
        risk_score = 40.0 if "Person" in event_type else 20.0
        if confidence > 0.8:
            risk_score += 10.0
            
        alert = Alert.objects.create(
            trip=trip,
            type='Vision',
            risk_score=risk_score,
            description=f"Vision Agent detected: {event_type} (Conf: {confidence})"
        )
        
        # In a real scenario, this would trigger the Risk Fusion Agent.
        
        return Response({
            "message": "Vision event processed",
            "alert": AlertSerializer(alert).data
        }, status=status.HTTP_201_CREATED)

class FusionRiskView(views.APIView):
    """
    Triggers the Risk Fusion Agent to calculate the current overall risk state 
    combining route, behavior, and vision data.
    """
    def get(self, request):
        trip_id = request.query_params.get('trip_id')
        
        if not trip_id:
            return Response({"error": "trip_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Mock implementation of risk fusion
        recent_alerts = trip.alerts.all()
        base_risk = sum(a.risk_score for a in recent_alerts) 
        
        # Max risk is 100
        final_risk = min(100.0, base_risk)
        
        # Decision Policy Mock Setup
        decision = "No Action"
        if final_risk >= 70:
            decision = "High Alert - Notify Control Room"
            trip.status = 'Alert'
            trip.save()
        elif final_risk >= 40:
            decision = "Warning - Notify Driver"
            
        return Response({
            "trip_id": trip.trip_id,
            "calculated_fusion_risk": final_risk,
            "decision": decision,
            "explanation": f"Calculated based on {recent_alerts.count()} recent events."
        })

class SimulationView(views.APIView):
    """
    Hackathon-specific endpoint to trigger the demo scenario 
    (injecting a person detection event and escalating risk).
    """
    def post(self, request):
        from .services.sms_service import SMSService
        
        trip_id = request.data.get('trip_id')
        
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Step 1: Inject a behavior alert (e.g. Unusual Stop)
        Alert.objects.create(
            trip=trip,
            type='Behavior',
            severity='Medium',
            risk_score=35.0,
            description="Behavior Agent: Stop duration exceeded 15 minutes."
        )

        # Step 2: Inject a vision alert 
        Alert.objects.create(
            trip=trip,
            type='Vision',
            severity='High',
            risk_score=45.0,
            description="Vision AI: Multiple persons detected near truck rear doors."
        )
        
        # Step 3: Trigger a system alert simulating Decision Engine action
        Alert.objects.create(
            trip=trip,
            type='System',
            severity='Critical',
            risk_score=80.0,
            description="Decision Engine: System locked container doors and notified police."
        )

        trip.status = 'Alert'
        trip.save()
        
        # Hackathon Demo Notification Fire
        phone_number = trip.truck.driver_phone or "+1234567890" 
        SMSService.send_alert(
            to_phone=phone_number,
            message=f"CRITICAL RAKSHAK ALERT:\nTrip {str(trip.trip_id)[:8]} is under threat! Container locked. Police notified."
        )

        return Response({
            "message": "Demo scenario executed. Risk escalated, alerts generated, SMS triggered.",
            "trip_id": trip.trip_id
        }, status=status.HTTP_200_OK)
