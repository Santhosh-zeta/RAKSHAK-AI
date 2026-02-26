from rest_framework import views, status
from rest_framework.response import Response
from .models import Trip, Alert
from .serializers import AlertSerializer
import datetime
import asyncio
import uuid
import base64
import json

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
# Perception Agent Bridge
# ===========================================================================
_perception_agent = None

def _get_perception_agent():
    """Lazily initialise the PerceptionAgent (YOLO + DeepSort loaded once)."""
    global _perception_agent
    if _perception_agent is None:
        from surveillance.agents.perception_agent import PerceptionAgent
        import redis.asyncio as aioredis
        import os

        agent = PerceptionAgent()
        
        # Load YOLO model
        from ultralytics import YOLO
        import torch
        agent.model = YOLO(agent.model_path)  # downloads yolov8n.pt on first run
        if torch.cuda.is_available():
            agent.model.to('cuda')
        agent.conf_threshold = 0.4
        agent.running = True

        # Connect Redis (used for publishing to PerceptionOutput channel)
        try:
            async def _connect():
                r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
                await r.ping()
                agent.redis = r
            asyncio.run(_connect())
        except Exception:
            agent.redis = None  # Redis down — still works, just won't publish

        _perception_agent = agent
    return _perception_agent

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


class PerceptionView(views.APIView):
    """
    HTTP bridge into the PerceptionAgent (YOLO + DeepSort).

    POST /api/agents/perception/
    Body: {
        "trip_id": "<uuid>",
        "truck_id": "TRK-001",          # optional, defaults to env TRUCK_ID
        "frame_b64": "<base64-encoded JPEG/PNG image>",
        "frame_id":  42                  # optional frame counter
    }

    Returns PerceptionOutput tracks + scene_tags, persists a Vision Alert
    if any person is detected, and publishes to Redis 'rakshak.perception.output'
    so BehaviourAgent can pick it up in real-time.
    """
    def post(self, request):
        from surveillance.agents.perception_agent import PerceptionOutput, Track, Velocity
        from datetime import datetime as dt

        trip_id   = request.data.get('trip_id')
        truck_id  = request.data.get('truck_id', 'TRK-001')
        frame_b64 = request.data.get('frame_b64')
        frame_id  = int(request.data.get('frame_id', 0))

        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not frame_b64:
            return Response({"error": "frame_b64 (base64 image) is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Decode base64 image
        try:
            frame_bytes = base64.b64decode(frame_b64)
        except Exception:
            return Response({"error": "Invalid base64 in frame_b64"}, status=status.HTTP_400_BAD_REQUEST)

        # Run YOLO + DeepSort
        try:
            agent = _get_perception_agent()
            tracks = agent._process_frame(frame_bytes)
        except Exception as e:
            return Response({"error": f"PerceptionAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Build scene tags
        current_hour = dt.now().hour
        scene_tags = agent._compute_scene_tags(tracks, current_hour)

        # Build full PerceptionOutput dict for Redis publishing
        perception_out = {
            "truck_id": truck_id,
            "frame_id": frame_id,
            "timestamp": dt.now().isoformat(),
            "tracks": [t.model_dump() for t in tracks],
            "scene_tags": scene_tags
        }

        # Publish to Redis so BehaviourAgent gets it in real-time
        if agent.redis:
            try:
                asyncio.run(agent.redis.publish(
                    agent.output_channel,
                    json.dumps(perception_out)
                ))
            except Exception:
                pass  # Non-fatal if Redis publish fails

        # Persist a Vision Alert for any person detections
        alert_obj = None
        person_tracks = [t for t in tracks if t.class_name == 'person']
        if person_tracks:
            max_conf   = max(t.confidence for t in person_tracks)
            risk_score = round(min(30.0 + max_conf * 50.0, 100.0), 2)
            severity   = 'Critical' if risk_score >= 80 else ('High' if risk_score >= 60 else 'Medium')
            loitering  = [t for t in person_tracks if t.dwell_seconds > 30]

            desc = (f"Perception Agent: {len(person_tracks)} person(s) detected. "
                    f"{'Loitering detected. ' if loitering else ''}"
                    f"Max confidence: {max_conf:.2f}. Tags: {scene_tags}.")

            alert_obj = Alert.objects.create(
                trip=trip,
                type='Vision',
                severity=severity,
                risk_score=risk_score,
                description=desc,
                ai_explanation=f"YOLO+DeepSort: {len(tracks)} total tracks, {len(person_tracks)} persons. Frame #{frame_id}."
            )

        tracks_data = [t.model_dump() for t in tracks]

        return Response({
            "frame_id": frame_id,
            "track_count": len(tracks),
            "person_count": len([t for t in tracks if t.class_name == 'person']),
            "scene_tags":  scene_tags,
            "tracks":      tracks_data,
            "alert_created": AlertSerializer(alert_obj).data if alert_obj else None,
            "published_to_redis": agent.redis is not None,
        }, status=status.HTTP_200_OK)

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


# ===========================================================================
# Digital Twin Agent Bridge
# ===========================================================================
_digital_twin_agent = None

def _get_digital_twin_agent():
    """Lazily initialise the DigitalTwinAgent (connects to Redis for baseline state)."""
    global _digital_twin_agent
    if _digital_twin_agent is None:
        from surveillance.agents.digital_twin_agent import DigitalTwinAgent
        import redis.asyncio as aioredis, os
        agent = DigitalTwinAgent()
        agent.running = True
        # Connect Redis for baseline lookups; fall back gracefully
        try:
            async def _connect():
                r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
                await r.ping()
                agent.redis = r
                await agent.start()  # loads baselines from Redis
            asyncio.run(_connect())
        except Exception:
            agent.redis = None
            # Patch baseline lookup to return default when Redis absent
            async def _default_baseline(tid): return {
                "expected_weight_kg": 2000.0,
                "expected_door_state": "CLOSED",
                "planned_route_center": {"lat": 28.6139, "lon": 77.2090},
                "max_deviation_km": 0.5
            }
            agent._get_baseline = _default_baseline
        _digital_twin_agent = agent
    return _digital_twin_agent


class DigitalTwinView(views.APIView):
    """
    HTTP bridge into the DigitalTwinAgent.

    POST /api/agents/digital-twin/
    Body (IoTTelemetry):  {
        "trip_id": "<uuid>",
        "truck_id": "TRK-001",
        "timestamp": "2026-02-26T10:00:00",
        "gps_lat": 13.08,  "gps_lon": 80.27,
        "door_state": "CLOSED",          # "OPEN" | "CLOSED"
        "cargo_weight_kg": 1950.0,
        "engine_on": true,
        "driver_rfid_scanned": true,
        "iot_signal_strength": 0.85     # 0.0-1.0
    }
    """
    def post(self, request):
        from surveillance.agents.digital_twin_agent import IoTTelemetry
        from datetime import datetime as dt

        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        # Build IoTTelemetry
        try:
            telemetry = IoTTelemetry(
                truck_id=request.data.get('truck_id', 'TRK-001'),
                timestamp=request.data.get('timestamp', dt.now().isoformat()),
                gps_lat=float(request.data.get('gps_lat', 0.0)),
                gps_lon=float(request.data.get('gps_lon', 0.0)),
                door_state=request.data.get('door_state', 'CLOSED'),
                cargo_weight_kg=float(request.data.get('cargo_weight_kg', 2000.0)),
                engine_on=bool(request.data.get('engine_on', True)),
                driver_rfid_scanned=bool(request.data.get('driver_rfid_scanned', True)),
                iot_signal_strength=float(request.data.get('iot_signal_strength', 1.0)),
            )
        except Exception as e:
            return Response({"error": f"Invalid payload: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = _get_digital_twin_agent()
            baseline = asyncio.run(agent._get_baseline(telemetry.truck_id))
            deviations, deviation_score = asyncio.run(agent._detect_deviations(telemetry, baseline))
            twin_status = agent._classify_status(deviation_score)
        except Exception as e:
            return Response({"error": f"DigitalTwinAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Publish to Redis so RouteAgent / RiskFusion can receive it
        if _digital_twin_agent and _digital_twin_agent.redis:
            try:
                payload = {
                    "truck_id": telemetry.truck_id,
                    "timestamp": dt.now().isoformat(),
                    "gps_lat": telemetry.gps_lat, "gps_lon": telemetry.gps_lon,
                    "door_state": telemetry.door_state,
                    "cargo_weight_kg": telemetry.cargo_weight_kg,
                    "engine_on": telemetry.engine_on,
                    "driver_rfid_scanned": telemetry.driver_rfid_scanned,
                    "deviation_score": deviation_score,
                    "deviations": deviations,
                    "twin_status": twin_status,
                    "iot_signal_fresh": True,
                }
                asyncio.run(_digital_twin_agent.redis.publish(
                    _digital_twin_agent.output_channel, json.dumps(payload)
                ))
            except Exception:
                pass

        # Persist alert if degraded or critical
        alert_obj = None
        if twin_status in ("DEGRADED", "CRITICAL"):
            risk_score = round(min(deviation_score * 100, 100.0), 2)
            severity = "Critical" if twin_status == "CRITICAL" else "High"
            alert_obj = Alert.objects.create(
                trip=trip, type='System', severity=severity,
                risk_score=risk_score,
                description=f"Digital Twin: {twin_status}. Issues: {'; '.join(deviations)}",
                ai_explanation=f"Deviation score: {deviation_score:.2f}. Baseline: {baseline}"
            )
            if risk_score >= 70 and trip.status not in ('Alert', 'Completed'):
                trip.status = 'Alert'
                trip.current_calculated_risk = risk_score
                trip.save()

        return Response({
            "twin_status": twin_status,
            "deviation_score": deviation_score,
            "deviations": deviations,
            "alert_created": AlertSerializer(alert_obj).data if alert_obj else None,
            "published_to_redis": _digital_twin_agent.redis is not None,
        }, status=status.HTTP_200_OK)


# ===========================================================================
# Route Agent Bridge
# ===========================================================================
_route_agent = None

def _get_route_agent():
    """Lazily initialise the RouteAgent with default geometry."""
    global _route_agent
    if _route_agent is None:
        from surveillance.agents.route_agent import RouteAgent
        import os, redis.asyncio as aioredis
        agent = RouteAgent()
        agent.running = True
        # Load corridors (default geometry if model not present)
        asyncio.run(agent._load_default_geometry())
        # Redis (optional)
        try:
            async def _connect():
                r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
                await r.ping()
                agent.redis = r
            asyncio.run(_connect())
        except Exception:
            agent.redis = None
        _route_agent = agent
    return _route_agent


class RouteView(views.APIView):
    """
    HTTP bridge into the RouteAgent (Shapely geofencing).

    POST /api/agents/route/
    Body: {
        "trip_id": "<uuid>",
        "truck_id": "TRK-001",
        "gps_lat": 28.61,  "gps_lon": 77.20
    }
    """
    def post(self, request):
        from shapely.geometry import Point
        from datetime import datetime as dt

        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            gps_lat = float(request.data.get('gps_lat'))
            gps_lon = float(request.data.get('gps_lon'))
        except (TypeError, ValueError):
            return Response({"error": "gps_lat and gps_lon are required floats"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = _get_route_agent()
            point = Point(gps_lon, gps_lat)
            hour = dt.now().hour
            in_safe, deviation_km, corridor_name = agent._check_safe_corridor(point)
            in_risk, risk_zone_name = agent._check_risk_zones(point)
            multiplier = agent._compute_time_multiplier(hour)
            route_risk = agent._compute_route_risk_score(in_safe, deviation_km, in_risk, multiplier)
        except Exception as e:
            return Response({"error": f"RouteAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Publish TwinOutput-compatible payload to Redis for RiskFusion
        if _route_agent and _route_agent.redis:
            try:
                payload = {
                    "truck_id": request.data.get('truck_id', 'TRK-001'),
                    "timestamp": dt.now().isoformat(),
                    "gps_lat": gps_lat, "gps_lon": gps_lon,
                    "in_safe_corridor": in_safe,
                    "deviation_km": deviation_km, "in_high_risk_zone": in_risk,
                    "high_risk_zone_name": risk_zone_name,
                    "route_risk_score": route_risk,
                    "time_multiplier": multiplier,
                    "nearest_corridor_name": corridor_name,
                }
                asyncio.run(_route_agent.redis.publish(
                    _route_agent.output_channel, json.dumps(payload)
                ))
            except Exception:
                pass

        # Persist alert for route violations
        alert_obj = None
        if not in_safe or in_risk:
            risk_score = round(min(route_risk * 100, 100.0), 2)
            severity = "Critical" if risk_score >= 80 else "High"
            reasons = []
            if not in_safe: reasons.append(f"Off safe corridor by {deviation_km:.2f}km")
            if in_risk:     reasons.append(f"In high-risk zone: {risk_zone_name}")
            alert_obj = Alert.objects.create(
                trip=trip, type='Route', severity=severity,
                risk_score=risk_score,
                description=f"Route Agent: {'; '.join(reasons)}.",
                ai_explanation=f"Shapely check: corridor={corridor_name}, multiplier={multiplier}"
            )
            if risk_score >= 70 and trip.status not in ('Alert', 'Completed'):
                trip.status = 'Alert'
                trip.current_calculated_risk = risk_score
                trip.save()

        return Response({
            "in_safe_corridor": in_safe,
            "deviation_km": deviation_km,
            "in_high_risk_zone": in_risk,
            "high_risk_zone_name": risk_zone_name,
            "route_risk_score": route_risk,
            "nearest_corridor": corridor_name,
            "alert_created": AlertSerializer(alert_obj).data if alert_obj else None,
            "published_to_redis": _route_agent.redis is not None,
        }, status=status.HTTP_200_OK)


# ===========================================================================
# Risk Fusion Agent Bridge  (weighted fallback, no Bayesian model required)
# ===========================================================================
_risk_fusion_agent = None

def _get_risk_fusion_agent():
    """Lazily initialise the RiskFusionAgent."""
    global _risk_fusion_agent
    if _risk_fusion_agent is None:
        from surveillance.agents.risk_fusion_agent import RiskFusionAgent
        import os, redis.asyncio as aioredis
        agent = RiskFusionAgent()
        agent.running = True
        try:
            async def _connect():
                r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
                await r.ping()
                agent.redis = r
            asyncio.run(_connect())
        except Exception:
            agent.redis = None
        _risk_fusion_agent = agent
    return _risk_fusion_agent


class RiskFusionView(views.APIView):
    """
    HTTP bridge into the RiskFusionAgent (weighted or Bayesian fusion).

    POST /api/agents/risk-fusion/
    Body: {
        "trip_id": "<uuid>",
        "truck_id": "TRK-001",
        "behaviour": { "anomaly_score": 0.75, "loitering_detected": true },
        "twin":      { "deviation_score": 0.5, "door_state": "OPEN", "driver_rfid_scanned": false },
        "route":     { "route_risk_score": 0.3, "in_safe_corridor": true, "in_high_risk_zone": false }
    }
    """
    def post(self, request):
        import uuid as _uuid

        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        signals = {
            "behaviour": request.data.get("behaviour", {}),
            "twin":      request.data.get("twin", {}),
            "route":     request.data.get("route", {}),
        }
        data_ages = {"behaviour": 0.0, "twin": 0.0, "route": 0.0, "temporal": 0.0}

        try:
            agent = _get_risk_fusion_agent()
            score, confidence, method = asyncio.run(agent._weighted_fusion(signals, data_ages))
            triggered = agent._get_triggered_rules(signals, score)
            risk_level = agent._classify_risk_level(score)
        except Exception as e:
            return Response({"error": f"RiskFusionAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Publish to rakshak.risk.output for DecisionAgent
        if _risk_fusion_agent and _risk_fusion_agent.redis:
            try:
                incident_id = str(_uuid.uuid4())
                pub_payload = {
                    "truck_id": request.data.get("truck_id", "TRK-001"),
                    "timestamp": __import__('datetime').datetime.now().isoformat(),
                    "incident_id": incident_id,
                    "composite_risk_score": score,
                    "risk_level": risk_level,
                    "confidence": confidence,
                    "component_scores": {
                        "behaviour": signals["behaviour"].get("anomaly_score", 0.0),
                        "twin": signals["twin"].get("deviation_score", 0.0),
                        "route": signals["route"].get("route_risk_score", 0.0),
                        "temporal": agent._get_temporal_score(),
                    },
                    "triggered_rules": triggered,
                    "fusion_method": method,
                }
                asyncio.run(_risk_fusion_agent.redis.publish(
                    _risk_fusion_agent.output_channel, json.dumps(pub_payload)
                ))
                # Also write scored key with TTL
                asyncio.run(_risk_fusion_agent.redis.setex(
                    f"risk_score:{request.data.get('truck_id', 'TRK-001')}", 60, str(score)
                ))
            except Exception:
                pass

        # Update trip's current risk
        risk_pct = round(score * 100, 2)
        trip.current_calculated_risk = risk_pct
        if risk_level in ("HIGH", "CRITICAL") and trip.status not in ('Alert', 'Completed'):
            trip.status = 'Alert'
        trip.save()

        return Response({
            "composite_risk_score": score,
            "risk_level": risk_level,
            "confidence": confidence,
            "fusion_method": method,
            "triggered_rules": triggered,
            "trip_risk_updated_to": risk_pct,
            "published_to_redis": _risk_fusion_agent.redis is not None,
        }, status=status.HTTP_200_OK)


# ===========================================================================
# Explainability Agent Bridge  (template / OpenAI / Ollama)
# ===========================================================================
class ExplainabilityView(views.APIView):
    """
    HTTP bridge into the ExplainabilityAgent.

    POST /api/agents/explain/
    Body: {
        "trip_id": "<uuid>",
        "incident_id": "<uuid>",
        "risk_payload":      { ...RiskOutput... },    # from RiskFusionView
        "decision_payload":  { ...DecisionOutput... } # from DecisionView
    }
    """
    def post(self, request):
        from surveillance.agents.explainability_agent import ExplainabilityAgent
        import time as _time

        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response({"error": "trip_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trip = Trip.objects.get(trip_id=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        risk_payload     = request.data.get("risk_payload", {})
        decision_payload = request.data.get("decision_payload", {})
        incident_id      = request.data.get("incident_id", str(uuid.uuid4()))

        try:
            agent = ExplainabilityAgent()
            asyncio.run(agent.start())
            t0 = _time.time()
            explanation_text, model_used = asyncio.run(
                agent._generate_explanation(decision_payload, risk_payload)
            )
            gen_ms = (_time.time() - t0) * 1000
        except Exception as e:
            return Response({"error": f"ExplainabilityAgent error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save explanation to the most recent Alert's ai_explanation field for this trip
        latest_alert = Alert.objects.filter(trip=trip).order_by('-timestamp').first()
        if latest_alert:
            latest_alert.ai_explanation = explanation_text
            latest_alert.save()

        return Response({
            "incident_id": incident_id,
            "explanation_text": explanation_text,
            "llm_model_used": model_used,
            "generation_time_ms": round(gen_ms, 2),
            "saved_to_alert": str(latest_alert.alert_id) if latest_alert else None,
        }, status=status.HTTP_200_OK)
