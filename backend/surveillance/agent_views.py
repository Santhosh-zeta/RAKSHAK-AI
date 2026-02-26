from rest_framework import views, status
from rest_framework.response import Response
from .models import Trip, Alert
from .serializers import AlertSerializer
import datetime
import asyncio
import uuid

# ===========================================================================
# Behaviour Agent Bridge
# ===========================================================================
_behaviour_agent = None

def _get_behaviour_agent():
    """Lazily initialise the BehaviourAgent (loads .pkl model if present)."""
    global _behaviour_agent
    if _behaviour_agent is None:
        from surveillance.agents.behavior_agent import BehaviourAgent
        agent = BehaviourAgent()
        asyncio.run(agent.start())
        _behaviour_agent = agent
    return _behaviour_agent

# ===========================================================================
# Decision Agent Bridge
# ===========================================================================
_decision_agent = None

def _get_decision_agent():
    """Lazily initialise the DecisionAgent (Redis optional — falls back to no cooldown)."""
    global _decision_agent
    if _decision_agent is None:
        from surveillance.agents.decision_agent import DecisionAgent
        agent = DecisionAgent()
        # Manually do what start() does without requiring Redis to be up
        agent.running = True
        try:
            import redis.asyncio as aioredis
            async def _try_connect():
                agent.redis = aioredis.from_url(agent.redis_url)
                # Ping to test connection
                await agent.redis.ping()
            asyncio.run(_try_connect())
        except Exception:
            agent.redis = None   # Redis not available — works fine

        # Patch cooldown + logging to be no-ops when Redis is unavailable
        if agent.redis is None:
            async def _no_cooldown(*args, **kwargs): return False
            async def _no_set_cooldown(*args, **kwargs): pass
            async def _no_log(*args, **kwargs): pass
            agent._is_on_cooldown = _no_cooldown
            agent._set_cooldown   = _no_set_cooldown
            agent._log_incident   = _no_log

        _decision_agent = agent
    return _decision_agent


class DecisionView(views.APIView):
    """
    HTTP bridge into the DecisionAgent written by the AI team.

    POST /api/agents/decision/
    Body: {
        "trip_id": "<uuid>",
        "truck_id": "TRK-001",
        "composite_risk_score": 0.88,   # 0.0 – 1.0 (from RiskFusion agent)
        "risk_level": "CRITICAL",
        "confidence": 0.92,
        "component_scores": {"vision": 0.9, "behaviour": 0.8},
        "triggered_rules": ["loitering", "night_activity"],
        "fusion_method": "weighted_sum"
    }
    """
    def post(self, request):
        from surveillance.agents.decision_agent import RiskInput

        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Build the RiskInput that the agent expects
        try:
            risk_input = RiskInput(
                truck_id=request.data.get('truck_id', str(trip.truck.truck_id)),
                incident_id=str(uuid.uuid4()),
                composite_risk_score=float(request.data.get('composite_risk_score', 0.0)),
                risk_level=request.data.get('risk_level', 'UNKNOWN'),
                confidence=float(request.data.get('confidence', 0.5)),
                component_scores=request.data.get('component_scores', {}),
                triggered_rules=request.data.get('triggered_rules', []),
                fusion_method=request.data.get('fusion_method', 'manual')
            )
        except Exception as e:
            return Response({"error": f"Invalid payload: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate score range
        if not (0.0 <= risk_input.composite_risk_score <= 1.0):
            return Response({"error": "composite_risk_score must be between 0.0 and 1.0"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Run the agent's rule engine
        try:
            agent = _get_decision_agent()
            output = asyncio.run(agent._evaluate_rules(risk_input))
        except Exception as e:
            return Response({"error": f"DecisionAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Persist a System alert if a rule fired and wasn't suppressed
        alert_obj = None
        if output.rule_id and not output.alert_suppressed:
            score_pct = round(risk_input.composite_risk_score * 100, 2)
            severity_map = {'R001': 'Critical', 'R002': 'High', 'R003': 'Medium'}
            severity = severity_map.get(output.rule_id, 'Medium')

            alert_obj = Alert.objects.create(
                trip=trip,
                type='Fusion',
                severity=severity,
                risk_score=min(score_pct, 100.0),
                description=(f"Decision Agent fired rule {output.rule_id} ({output.rule_name}). "
                             f"Actions: {', '.join(output.actions_taken) or 'none'}."),
                ai_explanation=(f"Rule matched at composite score {risk_input.composite_risk_score:.2f}. "
                                f"Triggered rules: {risk_input.triggered_rules}.")
            )

            # Escalate trip if critical or high
            if severity in ('Critical', 'High') and trip.status not in ('Alert', 'Completed'):
                trip.status = 'Alert'
                trip.current_calculated_risk = score_pct
                trip.save()

        return Response({
            "rule_fired": output.rule_id,
            "rule_name": output.rule_name,
            "actions_taken": output.actions_taken,
            "alert_suppressed": output.alert_suppressed,
            "suppression_reason": output.suppression_reason,
            "risk_score": output.risk_score,
            "risk_level": output.risk_level,
            "alert_created": AlertSerializer(alert_obj).data if alert_obj else None,
        }, status=status.HTTP_200_OK)

class BehaviourAnalysisView(views.APIView):
    """
    HTTP bridge into the BehaviourAgent written by the AI team.

    POST /api/agents/behaviour-analysis/
    Body: {
        "trip_id": "<uuid>",
        "truck_id": "<any string for the agent>",
        "tracks": [
            {
                "track_id": 1,
                "dwell_seconds": 45.0,
                "velocity": {"dx": 0.2, "dy": 0.1},
                "confidence": 0.88
            },
            ...
        ]
    }
    """
    def post(self, request):
        trip_id  = request.data.get('trip_id')
        truck_id = request.data.get('truck_id', 'TRK-001')
        tracks   = request.data.get('tracks', [])

        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(tracks, list):
            return Response({"error": "tracks must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # ── call the AI team's agent (sync wrapper around async method) ──
        try:
            agent = _get_behaviour_agent()
            payload = {"truck_id": truck_id, "tracks": tracks}
            output = asyncio.run(agent._process_perception_output(payload))
        except Exception as e:
            return Response({"error": f"BehaviourAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ── persist an Alert if the agent flagged an anomaly ──
        alert_obj = None
        if output.is_anomaly:
            risk_score = round(output.anomaly_score * 100, 2)   # 0–1 → 0–100

            if output.crowd_anomaly:
                alert_type = 'Behavior'
                desc = (f"Crowd anomaly: {len(output.flagged_track_ids)} tracks flagged. "
                        f"Anomaly score: {output.anomaly_score:.2f}")
            elif output.loitering_detected:
                alert_type = 'Behavior'
                desc = (f"Loitering detected for {output.loitering_duration_s:.0f}s. "
                        f"Flagged tracks: {output.flagged_track_ids}")
            else:
                alert_type = 'Behavior'
                desc = (f"Suspicious behaviour: anomaly score {output.anomaly_score:.2f}. "
                        f"Tracks: {output.flagged_track_ids}")

            severity = 'Critical' if risk_score >= 80 else ('High' if risk_score >= 60 else 'Medium')

            alert_obj = Alert.objects.create(
                trip=trip,
                type=alert_type,
                severity=severity,
                risk_score=min(risk_score, 100.0),
                description=desc,
                ai_explanation=f"IsolationForest raw scores: {output.raw_scores}"
            )

            # Escalate trip status if risk is high
            if risk_score >= 70 and trip.status not in ('Alert', 'Completed'):
                trip.status = 'Alert'
                trip.current_calculated_risk = risk_score
                trip.save()

        return Response({
            "is_anomaly": output.is_anomaly,
            "anomaly_score": output.anomaly_score,
            "loitering_detected": output.loitering_detected,
            "loitering_duration_s": output.loitering_duration_s,
            "crowd_anomaly": output.crowd_anomaly,
            "flagged_track_ids": output.flagged_track_ids,
            "alert_created": AlertSerializer(alert_obj).data if alert_obj else None,
        }, status=status.HTTP_200_OK)

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
