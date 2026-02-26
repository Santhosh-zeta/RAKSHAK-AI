# RAKSHAK-AI Backend — API Reference (Postman Guide)

> **Base URL**: `http://127.0.0.1:8000/api`  
> **Auth header** (required on every request):
> ```
> Authorization: Token b86bfe2487b02efc228b5e4bb0bb7692c3a166d6
> Content-Type: application/json
> ```
> Get a token by running: `python create_token.py` in the backend directory.

---

## 📦 CRUD Endpoints

### 1. List Trucks
```
GET /api/trucks/
```
No body required.

---

### 2. List Trips
```
GET /api/trips/
```
No body required.

---

### 3. List Alerts
```
GET /api/alerts/
```
No body required.

---

### 4. List GPS Logs
```
GET /api/gps-logs/
```
No body required.

---

### 5. Create GPS Log
```
POST /api/gps-logs/
```
```json
{
  "trip": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "speed": 60.5,
  "heading": 180.0,
  "timestamp": "2026-02-26T10:00:00Z"
}
```

---

## 🤖 Agent Endpoints

### 6. Behaviour Analysis Agent
Detects loitering and crowd anomalies from DeepSort tracks.
```
POST /api/agents/behaviour-analysis/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "tracks": [
    {
      "track_id": 1,
      "dwell_seconds": 65.0,
      "velocity": { "dx": 0.1, "dy": 0.05 },
      "confidence": 0.91
    },
    {
      "track_id": 2,
      "dwell_seconds": 12.0,
      "velocity": { "dx": 2.5, "dy": 1.2 },
      "confidence": 0.78
    }
  ]
}
```
**Response fields**: `is_anomaly`, `anomaly_score`, `loitering_detected`, `flagged_track_ids`, `alert_created`

---

### 7. Decision Agent
Evaluates composite risk score against R001/R002/R003 rules and fires SMS/email.
```
POST /api/agents/decision/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "composite_risk_score": 0.88,
  "risk_level": "CRITICAL",
  "confidence": 0.92,
  "component_scores": {
    "vision": 0.9,
    "behaviour": 0.85
  },
  "triggered_rules": ["loitering", "person_near_door"],
  "fusion_method": "weighted_sum"
}
```
**Rules**: R001 score ≥ 0.85 → CRITICAL | R002 ≥ 0.65 → HIGH | R003 ≥ 0.45 → MEDIUM  
**Response fields**: `rule_fired`, `rule_name`, `actions_taken`, `alert_suppressed`, `alert_created`

---

### 8. Digital Twin Agent
Processes IoT telemetry and detects cargo/door/GPS deviations.
```
POST /api/agents/digital-twin/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "timestamp": "2026-02-26T10:00:00",
  "gps_lat": 28.6139,
  "gps_lon": 77.2090,
  "door_state": "OPEN",
  "cargo_weight_kg": 2200.0,
  "engine_on": false,
  "driver_rfid_scanned": false,
  "iot_signal_strength": 0.2
}
```
**door_state**: `"OPEN"` or `"CLOSED"`  
**Response fields**: `twin_status` (NOMINAL/DEGRADED/CRITICAL), `deviation_score`, `deviations`, `alert_created`

---

### 9. Route Agent
Validates GPS coordinates against safe corridors and high-risk geofence zones (Shapely).
```
POST /api/agents/route/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "gps_lat": 28.8500,
  "gps_lon": 77.0900
}
```
**Response fields**: `in_safe_corridor`, `deviation_km`, `in_high_risk_zone`, `high_risk_zone_name`, `route_risk_score`, `nearest_corridor`, `alert_created`

> **Test case for violation**: use `gps_lat: 28.85, gps_lon: 77.09` (Narela Industrial Zone)  
> **Test case for safe route**: use `gps_lat: 28.61, gps_lon: 77.21` (Delhi corridor)

---

### 10. Risk Fusion Agent
Aggregates behaviour + twin + route scores using Bayesian/weighted fusion.
```
POST /api/agents/risk-fusion/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "behaviour": {
    "anomaly_score": 0.75,
    "loitering_detected": true
  },
  "twin": {
    "deviation_score": 0.60,
    "door_state": "OPEN",
    "driver_rfid_scanned": false
  },
  "route": {
    "route_risk_score": 0.40,
    "in_safe_corridor": false,
    "in_high_risk_zone": true
  }
}
```
**Response fields**: `composite_risk_score` (0.0–1.0), `risk_level` (LOW/MEDIUM/HIGH/CRITICAL), `confidence`, `fusion_method`, `triggered_rules`, `trip_risk_updated_to`

---

### 11. Explainability Agent
Generates a natural language explanation for an alert (template/OpenAI/Ollama).
```
POST /api/agents/explain/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "incident_id": "7f71f375-ed7d-4164-8b23-1c8e1c29d960",
  "risk_payload": {
    "composite_risk_score": 0.81,
    "risk_level": "HIGH",
    "confidence": 0.88,
    "component_scores": {
      "behaviour": 0.75,
      "twin": 0.60,
      "route": 0.40
    },
    "triggered_rules": ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID"],
    "fusion_method": "weighted_fallback"
  },
  "decision_payload": {
    "rule_name": "HIGH_RISK_ALERT",
    "actions_taken": ["email", "log_incident"]
  }
}
```
**Response fields**: `explanation_text`, `llm_model_used`, `generation_time_ms`, `saved_to_alert`

> To use OpenAI, set `OPENAI_API_KEY` in `.env` and `LLM_PROVIDER=openai`.  
> To use Ollama, set `LLM_PROVIDER=ollama` and `OLLAMA_HOST`.  
> Default is `rule_based_template` (no external API needed).

---

### 12. Perception Agent
Runs YOLO + DeepSort on a base64-encoded camera frame.
```
POST /api/agents/perception/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "truck_id": "TRK-001",
  "frame_id": 42,
  "frame_b64": "<base64-encoded JPEG image>"
}
```
> **How to generate frame_b64 in Python**:
> ```python
> import base64
> with open("test_frame.jpg", "rb") as f:
>     b64 = base64.b64encode(f.read()).decode()
> ```
**Response fields**: `track_count`, `person_count`, `scene_tags`, `tracks`, `alert_created`, `published_to_redis`

---

### 13. Legacy: Vision Event
```
POST /api/agents/vision-event/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "event_type": "Person Detected",
  "confidence": 0.92,
  "timestamp": "2026-02-26T10:00:00Z"
}
```

---

### 14. Legacy: Fusion Risk (Old)
```
POST /api/agents/fusion-risk/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8",
  "vision_risk": 40.0,
  "route_risk": 25.0,
  "behavioral_risk": 30.0
}
```

---

### 15. Demo Simulation
Triggers a full high-alert simulation scenario for a trip (for demonstrations).
```
POST /api/agents/simulate/
```
```json
{
  "trip_id": "ce6c07de-5060-4919-8bd6-69580cf1b3f8"
}
```

---

## 🔒 Authentication Test

### Without token → 401
```
GET /api/trucks/
```
_(no Authorization header)_

### Get your token
```bash
cd backend
python create_token.py
```

---

## 📋 Postman Environment Setup

Create a Postman **Environment** with these variables:

| Variable | Value |
|---|---|
| `base_url` | `http://127.0.0.1:8000/api` |
| `token` | `b86bfe2487b02efc228b5e4bb0bb7692c3a166d6` |
| `trip_id` | `ce6c07de-5060-4919-8bd6-69580cf1b3f8` |

Add this to every request's **Headers** tab:
```
Authorization: Token {{token}}
Content-Type: application/json
```

---

## ⚡ Full Pipeline Test Order

Run in this order to simulate a real cargo security event:

1. `POST /agents/perception/` — detect persons in camera frame
2. `POST /agents/behaviour-analysis/` — flag loitering
3. `POST /agents/digital-twin/` — check IoT deviations
4. `POST /agents/route/` — check geofence
5. `POST /agents/risk-fusion/` — fuse all 3 scores
6. `POST /agents/decision/` — fire alert rules
7. `POST /agents/explain/` — generate explanation
8. `GET /alerts/` — see all saved alerts
