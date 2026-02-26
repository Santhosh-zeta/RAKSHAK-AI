# RAKSHAK-AI Backend — Complete API Reference & Workflow Guide

> **Base URL:** `http://127.0.0.1:8000/api`  
> **Auth:** All endpoints (except login & register-company) require `Authorization: Token <your_token>` header.  
> **Format:** All request/response bodies are `application/json`.

---

## 📦 Table of Contents

1. [How to Run the Backend](#1-how-to-run-the-backend)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Postman / Client Setup](#3-postman--client-setup)
4. [Authentication Endpoints](#4-authentication-endpoints)
5. [Core CRUD Endpoints](#5-core-crud-endpoints)
6. [Admin Panel Endpoints](#6-admin-panel-endpoints)
7. [AI Agent Pipeline — Full Workflow](#7-ai-agent-pipeline--full-workflow)
8. [Quick End-to-End Simulation](#8-quick-end-to-end-simulation)
9. [Checking Results](#9-checking-results)
10. [Running the Automated Test Suite](#10-running-the-automated-test-suite)

---

## 1. How to Run the Backend

### Prerequisites

Make sure you have **Python 3.11+** installed.

### Step-by-Step Setup

```bash
# 1. Navigate to the backend directory
cd RAKSHAK-AI/backend

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Install all Python dependencies
pip install -r requirements.txt

# 4. Copy environment configuration (edit values as needed)
cp .env.example .env              # or manually set the values below

# 5. Apply database migrations (creates SQLite DB on first run)
python manage.py migrate

# 6. (First time only) Create a superuser admin account
python manage.py createsuperuser
#   → Enter: username=admin, email=admin@rakshak.ai, password=Rakshak@123

# 7. (Optional) Seed demo data — trucks, trips, companies
python manage.py loaddata fixtures/demo_data.json   # if fixture exists

# 8. Start the development server
python manage.py runserver 8000
```

The API will be live at: **`http://127.0.0.1:8000/api/`**

### Environment Variables (`.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL or SQLite URL | `sqlite:///db.sqlite3` |
| `REDIS_URL` | Redis for agent pub/sub | `redis://localhost:6379` |
| `TRUCK_ID` | Default truck identity tag | `TRK-001` |
| `OPENAI_API_KEY` | OpenAI key (Explainability Agent) | *(empty = template mode)* |
| `LLM_PROVIDER` | `openai`, `ollama`, or `template` | `template` |
| `TWILIO_SID` | Twilio Account SID (SMS alerts) | *(empty = SMS suppressed)* |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | *(empty)* |
| `TWILIO_PHONE` | Twilio sender number | *(empty)* |
| `SMTP_HOST` | Email SMTP host | `smtp.gmail.com` |
| `SMTP_USER` | SMTP username | *(empty)* |
| `SMTP_PASSWORD` | SMTP app password | *(empty)* |

> **Note:** Redis is **optional**. All AI agents fall back gracefully to stateless mode if Redis is unavailable — they just won't publish events between agents or use cooldown deduplication.

### Generate a Token Without Logging In

```bash
# Quickly create an auth token for the admin user (useful for testing)
python create_token.py
# → Prints: Token abc123...
```

---

## 2. System Architecture Overview

```
Camera Frame / IoT Sensor
        │
        ▼
┌───────────────────┐
│  PerceptionAgent  │  ← YOLOv8 + DeepSort tracker
│  (Computer Vision)│    Detects people/vehicles in frame
└────────┬──────────┘    Publishes to: rakshak.perception.output
         │
         ▼
┌───────────────────┐
│  BehaviourAgent   │  ← IsolationForest ML model (behavior_model.pkl)
│  (Anomaly Detect) │    Detects loitering, crowd anomalies, suspicious movement
└────────┬──────────┘    Publishes to: rakshak.behaviour.output
         │
         │         ┌──────────────────────┐
         │         │   DigitalTwinAgent   │  ← IoT telemetry: door state,
         │         │   (IoT Validation)   │    cargo weight, RFID, GPS
         │         └──────────┬───────────┘    Publishes to: rakshak.twin.output
         │                    │
         │         ┌──────────┘
         │         │         ┌─────────────────────┐
         │         │         │     RouteAgent       │  ← Shapely geofencing
         │         │         │  (Geospatial Check)  │    Safe corridors + risk zones
         │         │         └──────────┬───────────┘    Publishes to: rakshak.route.output
         │         │                    │
         └─────────┴────────────────────┘
                             │
                             ▼
                   ┌──────────────────────┐
                   │   RiskFusionAgent    │  ← Weighted/Bayesian aggregator
                   │  (Multi-Signal Risk) │    Combines behaviour + twin + route
                   └──────────┬───────────┘    Publishes to: rakshak.risk.output
                              │
                              ▼
                   ┌──────────────────────┐
                   │   DecisionAgent      │  ← Rule engine: R001/R002/R003
                   │  (Action Trigger)    │    Fires SMS / Email / log per risk level
                   └──────────┬───────────┘    Publishes to: rakshak.decision.output
                              │
                              ▼
                   ┌──────────────────────┐
                   │ ExplainabilityAgent  │  ← LLM (OpenAI / Ollama / template)
                   │  (Human Explanation) │    Generates natural language alert text
                   └──────────────────────┘    Publishes to: rakshak.explain.output
```

Each agent has **two modes**:
- **Streaming mode** — subscribes to Redis pub/sub channels, runs autonomously
- **HTTP mode** — called directly via REST API (used in this guide), no Redis required

---

## 3. Postman / Client Setup

1. Open Postman → **Environments** → **New Environment** → Name it `RAKSHAK-AI`
2. Add these variables:

| Variable | Initial Value |
|---|---|
| `base_url` | `http://127.0.0.1:8000/api` |
| `token` | *(fill after login)* |
| `trip_id` | *(fill after listing trips)* |
| `truck_id` | *(fill after listing trucks)* |
| `company_id` | *(fill after listing companies)* |

3. For every request after Step 4 (Auth), add this **Header**:
   - `Authorization` → `Token {{token}}`
   - `Content-Type` → `application/json`

---

## 4. Authentication Endpoints

### 4.1 Register a New Company (Public — No Token Required)

**What happens internally:**
- Creates a new `LogisticsCompany` record in the database
- Creates a Django `User` with the given credentials
- Creates a `CompanyUser` profile linking the user to the company with role `company_user`
- Generates and returns an auth `Token` for immediate use

```
POST {{base_url}}/auth/register-company/
```
```json
{
  "company_name": "NextGen Logistics",
  "company_city": "Delhi",
  "username":     "nextgen_admin",
  "password":     "SecurePass123",
  "email":        "admin@nextgen.com",
  "first_name":   "Raj",
  "last_name":    "Kumar"
}
```

**Response:**
```json
{
  "message": "Company registered successfully.",
  "token":   "abc123...",
  "user":    { "username": "nextgen_admin", "role": "company_user", ... },
  "company": { "company_id": "uuid...", "name": "NextGen Logistics", ... }
}
```
✅ **Action:** Copy `token` → paste into Postman env variable `token`.

---

### 4.2 Login Existing User

**What happens internally:**
- Calls Django's `authenticate()` to verify credentials
- Returns or creates a persistent `Token` for the user
- Returns the user's role and linked company info

```
POST {{base_url}}/auth/login/
```
```json
{
  "username": "admin",
  "password": "Rakshak@123"
}
```

**Response:**
```json
{
  "token":   "786c760b...",
  "user":    { "username": "admin", "role": "admin", ... },
  "company": null
}
```
✅ **Action:** Copy `token` → paste into Postman env `token`.

---

### 4.3 Get Current User Profile

**What happens internally:** Reads the `CompanyUser` profile linked to the token's user.

```
GET {{base_url}}/auth/me/
Headers: Authorization: Token {{token}}
```

---

### 4.4 Change Password

```
POST {{base_url}}/auth/change-password/
```
```json
{
  "old_password": "Rakshak@123",
  "new_password": "NewSecurePass456"
}
```

> **Note:** After changing password, your current token is invalidated and a new one is returned.

---

### 4.5 Logout

```
POST {{base_url}}/auth/logout/
```
Deletes the current token from the database. The session is immediately invalidated.

---

### 4.6 Register a New User (Admin Only)

**What happens internally:** Platform admin creates a company-scoped user (company_user or viewer role).

```
POST {{base_url}}/auth/register/
```
```json
{
  "username":   "fleet_manager_01",
  "password":   "FleetPass123",
  "email":      "fm@nextgen.com",
  "role":       "company_user",
  "company_id": "{{company_id}}"
}
```

---

## 5. Core CRUD Endpoints

> All endpoints below require `Authorization: Token {{token}}`.  
> **Company-scoped users** (role=`company_user` or `viewer`) automatically see only their own company's data.  
> **Admin users** (role=`admin`) see all companies' data.

---

### 5.1 Companies

#### List All Companies
```
GET {{base_url}}/companies/
```

**What happens internally:** Queries `LogisticsCompany` table, filtered by the requesting user's linked company (unless admin).

#### Get Company Detail
```
GET {{base_url}}/companies/{{company_id}}/
```

#### Get Company's Trucks
```
GET {{base_url}}/companies/{{company_id}}/trucks/
```

#### Get Company's Alerts (last 50)
```
GET {{base_url}}/companies/{{company_id}}/alerts/
```

#### Get Company Statistics
```
GET {{base_url}}/companies/{{company_id}}/stats/
```
**Returns:** Total trucks, active trucks, total trips, alert trips, unresolved critical alerts.

---

### 5.2 Trucks

#### List All Trucks
```
GET {{base_url}}/trucks/
```
✅ **Action:** Copy a `truck_id` (e.g., `8dc6b22e-...`) → paste into Postman env `truck_id`.

#### Optional Filters
```
GET {{base_url}}/trucks/?active=true
GET {{base_url}}/trucks/?company_id={{company_id}}
```

#### Create a Truck
```
POST {{base_url}}/trucks/
```
```json
{
  "company":       "{{company_id}}",
  "driver_name":   "Suresh Patel",
  "driver_phone":  "+919876543210",
  "driver_email":  "suresh@nextgen.com",
  "license_plate": "MH-01-AB-1234",
  "cargo_type":    "Electronics",
  "cargo_value":   500000.00
}
```

---

### 5.3 Trips

#### List All Trips
```
GET {{base_url}}/trips/
```
✅ **Action:** Copy a `trip_id` from an `In-Transit` trip → paste into Postman env `trip_id`.

#### Optional Filters
```
GET {{base_url}}/trips/?status=In-Transit
GET {{base_url}}/trips/?truck_id={{truck_id}}
```

#### Create a Trip

**What happens internally:**
- Saves the trip to the database
- Calls `GeoSpatialService.get_coordinates()` to geocode start/end locations
- Calls `GeoSpatialService.calculate_route()` to compute estimated distance
- Calculates a `baseline_route_risk` score based on distance and location names
- Saves all this to the `Trip` record

```
POST {{base_url}}/trips/
```
```json
{
  "truck":                  "{{truck_id_uuid}}",
  "start_location_name":    "Delhi Depot",
  "destination_name":       "Jaipur Warehouse",
  "start_time":             "2026-03-01T08:00:00Z",
  "estimated_arrival":      "2026-03-01T14:00:00Z",
  "status":                 "Scheduled"
}
```

#### Get Trip Live Dashboard
```
GET {{base_url}}/trips/{{trip_id}}/dashboard/
```
**Returns:** Current status, risk score, latest GPS fix, 5 most recent alerts.

---

### 5.4 GPS Logs

#### Log a GPS Position
```
POST {{base_url}}/gps-logs/
```
```json
{
  "trip":          "{{trip_id}}",
  "latitude":      28.6139,
  "longitude":     77.2090,
  "speed_kmh":     65.0,
  "heading":       180.0,
  "engine_status": true,
  "door_sealed":   true
}
```

#### List GPS Logs for a Trip
```
GET {{base_url}}/gps-logs/?trip_id={{trip_id}}
```

---

### 5.5 Alerts

#### List All Alerts
```
GET {{base_url}}/alerts/
```

#### Optional Filters
```
GET {{base_url}}/alerts/?trip_id={{trip_id}}
GET {{base_url}}/alerts/?severity=Critical
GET {{base_url}}/alerts/?resolved=false
```

#### Resolve an Alert
```
POST {{base_url}}/alerts/{{alert_id}}/resolve/
```

#### Resend Notifications for an Alert
```
POST {{base_url}}/alerts/{{alert_id}}/resend_notifications/
```

---

## 6. Admin Panel Endpoints

> These require role=`admin`. Company-scoped users will receive `403 Forbidden`.

#### Platform Dashboard Stats
```
GET {{base_url}}/admin/dashboard/
```
**Returns:** Total companies, users, trucks, trips, active trips and alerts across the entire platform.

#### List All Companies (Admin View)
```
GET {{base_url}}/admin/companies/
```

#### List All Users (Admin View)
```
GET {{base_url}}/admin/users/
```

#### Get / Update / Delete a Specific User
```
GET    {{base_url}}/admin/users/{{user_pk}}/
PATCH  {{base_url}}/admin/users/{{user_pk}}/
DELETE {{base_url}}/admin/users/{{user_pk}}/
```

#### List All Alerts (Admin View)
```
GET {{base_url}}/admin/alerts/
```

---

## 7. AI Agent Pipeline — Full Workflow

> Run these **in order** to simulate one complete cargo security cycle.  
> Each agent builds on the previous agent's output.

---

### Step 1 — Perception Agent (YOLO + DeepSort)

**What happens internally, step by step:**
1. The base64 image string is decoded back to raw JPEG/PNG bytes
2. OpenCV (`cv2.imdecode`) converts the bytes to a numpy frame array
3. **YOLOv8** (`yolov8n.pt`) runs object detection — identifies people, cars, trucks
4. Detections with confidence > 0.4 are selected
5. **DeepSort** tracker assigns persistent `track_id`s across frames, tracking each object as it moves
6. For each confirmed track: centroid history is updated, dwell time is computed (time since first seen), velocity (dx, dy) is estimated from the last 2 centroids
7. If any `person` is detected, a `Vision` alert is saved to the database with severity based on confidence
8. The full `PerceptionOutput` (tracks + scene_tags) is **published to Redis** `rakshak.perception.output` for the BehaviourAgent to pick up in real-time

```
POST {{base_url}}/agents/perception/
```
```json
{
  "trip_id":    "{{trip_id}}",
  "truck_id":   "TRK-001",
  "frame_id":   42,
  "frame_b64":  "<base64_encoded_jpeg_string>"
}
```

**To encode an image in Python:**
```python
import base64
with open("frame.jpg", "rb") as f:
    frame_b64 = base64.b64encode(f.read()).decode()
```

**Response:**
```json
{
  "frame_id":           42,
  "track_count":        2,
  "person_count":       1,
  "scene_tags":         ["loitering_detected"],
  "tracks":             [ { "track_id": 1, "class_name": "person", "confidence": 0.87, ... } ],
  "alert_created":      { "alert_id": "...", "severity": "High", "risk_score": 73.5 },
  "published_to_redis": false
}
```

✅ **Copy `tracks` array** → use as input to the next step.

---

### Step 2 — Behaviour Analysis Agent (IsolationForest ML)

**What happens internally, step by step:**
1. For each track received, 11 features are extracted:
   - `dwell_time`, `velocity_mean`, `velocity_std`, `direction_changes`
   - `proximity_to_cargo_door` (1 if dwell > 20s), `person_count_near_truck`
   - `night_time_flag`, `driver_absent_flag`, `unusual_vehicle_flag`
   - `time_since_last_authorized_scan`, `shift_hour`
2. The pre-trained **IsolationForest pipeline** (`behavior_model.pkl`) runs `.decision_function()` on the features — more negative = more anomalous
3. Scores are normalized to [0.0, 1.0] range
4. Tracks above the anomaly threshold (default: 0.6) are flagged
5. **Loitering detection:** tracks with `dwell_seconds > 30` that are also flagged
6. **Crowd anomaly:** > 4 tracks present + overall score > 0.5
7. If anomaly detected: a `Behavior` alert is created in the DB, trip status escalated to `Alert` if risk ≥ 70
8. `BehaviourOutput` published to Redis `rakshak.behaviour.output`

```
POST {{base_url}}/agents/behaviour-analysis/
```
```json
{
  "trip_id":  "{{trip_id}}",
  "truck_id": "TRK-001",
  "tracks": [
    {
      "track_id":      1,
      "dwell_seconds": 65.0,
      "velocity":      { "dx": 0.1, "dy": 0.05 },
      "confidence":    0.91
    },
    {
      "track_id":      2,
      "dwell_seconds": 80.0,
      "velocity":      { "dx": 0.0, "dy": 0.0 },
      "confidence":    0.85
    }
  ]
}
```

**Response:**
```json
{
  "is_anomaly":          true,
  "anomaly_score":       0.78,
  "loitering_detected":  true,
  "loitering_duration_s": 80.0,
  "crowd_anomaly":       false,
  "flagged_track_ids":   [1, 2],
  "alert_created":       { "severity": "High", "risk_score": 78.0, ... }
}
```

✅ **Note `anomaly_score`** → use as `behaviour.anomaly_score` in Risk Fusion (Step 5).

---

### Step 3 — Digital Twin Agent (IoT Telemetry Validator)

**What happens internally, step by step:**
1. An `IoTTelemetry` object is built from the request payload
2. The agent fetches the **baseline** for this truck from Redis (or uses a default: weight=2000kg, door=CLOSED, coordinates=Delhi)
3. **Deviation checks run in sequence:**
   - **Door state mismatch:** Door `OPEN` but RFID not scanned → deviation
   - **Cargo weight mismatch:** Weight differs from baseline by > 50kg → deviation
   - **GPS deviation:** Haversine distance from expected route center > `max_deviation_km` → deviation
   - **Engine + RFID:** Engine off but RFID not scanned → deviation
   - **Signal strength:** IoT signal < 0.3 → deviation (potential jamming)
4. A **deviation score** (0.0–1.0) is calculated based on number and severity of violations
5. Twin status classified: `NOMINAL` (< 0.3), `DEGRADED` (< 0.6), `CRITICAL` (≥ 0.6)
6. If DEGRADED or CRITICAL: alert saved, trip escalated
7. Full telemetry + deviation results published to Redis `rakshak.twin.output`

```
POST {{base_url}}/agents/digital-twin/
```
```json
{
  "trip_id":              "{{trip_id}}",
  "truck_id":             "TRK-001",
  "timestamp":            "2026-02-26T22:30:00",
  "gps_lat":              28.6139,
  "gps_lon":              77.2090,
  "door_state":           "OPEN",
  "cargo_weight_kg":      500.0,
  "engine_on":            false,
  "driver_rfid_scanned":  false,
  "iot_signal_strength":  0.15
}
```

**Response:**
```json
{
  "twin_status":      "CRITICAL",
  "deviation_score":  0.82,
  "deviations":       ["door_open_no_rfid", "cargo_weight_mismatch", "signal_too_low"],
  "alert_created":    { "severity": "Critical", "risk_score": 82.0, ... },
  "published_to_redis": false
}
```

✅ **Note `deviation_score`** → use as `twin.deviation_score` in Risk Fusion (Step 5).

---

### Step 4 — Route Agent (Shapely Geofencing)

**What happens internally, step by step:**
1. GPS coordinates are converted to a `shapely.geometry.Point(lon, lat)` object
2. **Safe corridor check:** The point is tested against pre-defined safe route polygons (NH-48 Delhi-Jaipur corridor, etc.). If outside, `deviation_km` is computed as the distance to the nearest corridor edge
3. **High-risk zone check:** The point is tested against known risk zone polygons (Narela Industrial Area, Tughlakabad etc.)
4. **Time multiplier:** Risk is amplified at night (22:00–05:00 → ×2.0) or during peak hours (06:00–09:00 → ×1.3)
5. **Route risk score** = base deviation score × time multiplier, capped at 1.0
6. If off-corridor or in risk zone: `Route` alert saved, trip escalated
7. Results published to Redis `rakshak.route.output`

```
POST {{base_url}}/agents/route/
```
```json
{
  "trip_id":  "{{trip_id}}",
  "truck_id": "TRK-001",
  "gps_lat":  28.8500,
  "gps_lon":  77.0900
}
```

> 💡 `28.85, 77.09` = Narela Industrial Area (high-risk zone simulation)

**Response:**
```json
{
  "in_safe_corridor":    false,
  "deviation_km":        3.4,
  "in_high_risk_zone":   true,
  "high_risk_zone_name": "Narela Industrial Area",
  "route_risk_score":    0.72,
  "nearest_corridor":    "NH-48 Delhi-Jaipur",
  "alert_created":       { "severity": "High", "risk_score": 72.0, ... },
  "published_to_redis":  false
}
```

✅ **Note `route_risk_score`** → use as `route.route_risk_score` in Risk Fusion (Step 5).

---

### Step 5 — Risk Fusion Agent (Weighted / Bayesian Aggregator)

**What happens internally, step by step:**
1. Receives 3 signal dicts: `behaviour`, `twin`, `route`
2. **Quality-adjusted weighting:**
   - Base weights: behaviour=35%, twin=30%, route=25%, temporal=10%
   - Each weight is multiplied by `exp(-0.01 × data_age_seconds)` to penalise stale data
3. **Weighted fusion formula:**
   `composite = (w_b × anomaly + w_t × deviation + w_r × route_risk + w_time × temporal) / total_weight`
4. **Temporal score:** Automatically computed from current time: night hours (22–05) → 0.8, peak hours → 0.4, daytime → 0.1
5. **Rule triggers** are evaluated: LOITERING_DETECTED, DOOR_OPEN_NO_RFID, GEOFENCE_VIOLATION, HIGH_RISK_ZONE_ENTRY, CRITICAL_THRESHOLD_BREACH
6. **Risk level classification:** < 0.45 → LOW, < 0.65 → MEDIUM, < 0.85 → HIGH, ≥ 0.85 → CRITICAL
7. Trip's `current_calculated_risk` is updated in the database
8. The risk output is published to Redis `rakshak.risk.output` for DecisionAgent

```
POST {{base_url}}/agents/risk-fusion/
```
```json
{
  "trip_id":  "{{trip_id}}",
  "truck_id": "TRK-001",
  "behaviour": {
    "anomaly_score":      0.78,
    "loitering_detected": true
  },
  "twin": {
    "deviation_score":      0.82,
    "door_state":           "OPEN",
    "driver_rfid_scanned":  false
  },
  "route": {
    "route_risk_score":   0.72,
    "in_safe_corridor":   false,
    "in_high_risk_zone":  true,
    "deviation_km":       3.4
  }
}
```

**Response:**
```json
{
  "composite_risk_score":  0.77,
  "risk_level":            "HIGH",
  "confidence":            0.91,
  "fusion_method":         "weighted_fallback",
  "triggered_rules":       ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID", "GEOFENCE_VIOLATION"],
  "trip_risk_updated_to":  77.0,
  "published_to_redis":    false
}
```

✅ **Copy `composite_risk_score`, `risk_level`, `triggered_rules`** → use in Step 6.

---

### Step 6 — Decision Agent (Rule Engine)

**What happens internally, step by step:**
1. `RiskInput` is built from the request payload
2. Rules are evaluated in priority order:
   - **R001 CRITICAL_THEFT_ALERT** — score ≥ 0.85 → actions: SMS + email + log_incident
   - **R002 HIGH_RISK_ALERT** — score 0.65–0.84 → actions: email + log_incident
   - **R003 MEDIUM_RISK_MONITOR** — score 0.45–0.64 → actions: log_incident only
3. **Cooldown check:** Redis key `alert_cooldown:{truck_id}:{rule_id}` is checked — if active, the alert is suppressed to prevent spam (cooldowns: 5min / 10min / 30min)
4. **Actions executed:**
   - SMS: Twilio API (if configured), else logged as suppressed
   - Email: SMTP (if configured), else logged as suppressed
   - Log: stored in Redis list `incidents:{truck_id}`, TTL 24h
5. If R001 or R002 fires without suppression: a `Fusion` alert is saved to the DB, trip escalated to `Alert`
6. `DecisionOutput` published to Redis `rakshak.decision.output` for ExplainabilityAgent

```
POST {{base_url}}/agents/decision/
```
```json
{
  "trip_id":               "{{trip_id}}",
  "truck_id":              "TRK-001",
  "composite_risk_score":  0.77,
  "risk_level":            "HIGH",
  "confidence":            0.91,
  "component_scores": {
    "behaviour": 0.78,
    "twin":      0.82
  },
  "triggered_rules": ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID"],
  "fusion_method":   "weighted_fallback"
}
```

**Response:**
```json
{
  "rule_fired":         "R002",
  "rule_name":          "HIGH_RISK_ALERT",
  "actions_taken":      ["email", "log_incident"],
  "alert_suppressed":   false,
  "suppression_reason": null,
  "risk_score":         0.77,
  "risk_level":         "HIGH",
  "alert_created":      { "severity": "High", "risk_score": 77.0, ... }
}
```

---

### Step 7 — Explainability Agent (LLM / Template)

**What happens internally, step by step:**
1. A structured prompt is built from both `risk_payload` and `decision_payload` — includes truck ID, timestamp, all sensor scores, triggered rules, and actions taken
2. **LLM selection** (from `LLM_PROVIDER` env variable):
   - `openai` → calls OpenAI `gpt-4o-mini` API
   - `ollama` → calls local Ollama server (e.g., llama3)
   - `template` (default) → generates a rule-based plain English explanation without any API calls
3. The generated text is saved to the most recent Alert's `ai_explanation` field in the DB
4. Generation time is measured and returned

```
POST {{base_url}}/agents/explain/
```
```json
{
  "trip_id":     "{{trip_id}}",
  "incident_id": "7f71f375-ed7d-4164-8b23-1c8e1c29d960",
  "risk_payload": {
    "truck_id":              "TRK-001",
    "risk_level":            "HIGH",
    "composite_risk_score":  0.77,
    "confidence":            0.91,
    "component_scores": {
      "behaviour": 0.78,
      "twin":      0.82,
      "route":     0.72
    },
    "triggered_rules": ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID"],
    "fusion_method":   "weighted_fallback"
  },
  "decision_payload": {
    "rule_name":    "HIGH_RISK_ALERT",
    "actions_taken": ["email", "log_incident"]
  }
}
```

**Response:**
```json
{
  "incident_id":        "7f71f375-...",
  "explanation_text":   "Security alert generated for truck TRK-001 at 2026-02-26T22:35:01. The system has classified this as HIGH risk with a composite score of 0.77. Sensor data indicates: LOITERING_DETECTED, DOOR_OPEN_NO_RFID. Actions taken: email, log_incident.",
  "llm_model_used":     "rule_based_template",
  "generation_time_ms": 0.12,
  "saved_to_alert":     "alert_uuid..."
}
```

---

## 8. Quick End-to-End Simulation

Don't want to call all 7 agents manually? Use the **simulation endpoint** to instantly inject a full threat scenario into any trip:

**What happens internally:**
1. Creates 3 pre-set alerts on the trip: Behavior (Medium, 35%), Vision (High, 45%), System (Critical, 80%)
2. Sets trip status to `Alert`
3. Fires an SMS via Twilio (if configured) to the driver's phone number

```
POST {{base_url}}/agents/simulate/
```
```json
{
  "trip_id": "{{trip_id}}"
}
```

**Response:**
```json
{
  "message": "Demo scenario executed. Risk escalated, alerts generated, SMS triggered.",
  "trip_id": "5dc8969d-..."
}
```

---

### Legacy Endpoints (Still Fully Working)

#### Vision Event (Simple Object Detection Bridge)
```
POST {{base_url}}/agents/vision-event/
```
```json
{
  "trip_id":    "{{trip_id}}",
  "event_type": "Person Detected",
  "confidence": 0.94
}
```

#### Fusion Risk GET (Simplified Legacy Aggregator)
```
GET {{base_url}}/agents/fusion-risk/?trip_id={{trip_id}}
```

---

## 9. Checking Results

After running the pipeline, verify everything was persisted correctly:

#### Review Alerts on the Trip
```
GET {{base_url}}/alerts/?trip_id={{trip_id}}
```

#### Check Trip Status and Current Risk
```
GET {{base_url}}/trips/{{trip_id}}/dashboard/
```

#### Review All Critical Alerts (Platform-Wide)
```
GET {{base_url}}/admin/alerts/?severity=Critical
```

---

## 10. Running the Automated Test Suite

The backend ships with a complete test script that validates all 59 API calls:

```bash
# Make sure the server is running first:
python manage.py runserver 8000

# In a separate terminal, run the full test suite:
cd RAKSHAK-AI/backend
source venv/bin/activate
python test_all_apis.py
```

**What the test covers:**

| Section | Tests |
|---|---|
| Auth (login, me, bad creds, missing fields) | 4 |
| Companies CRUD (list, detail, trucks, alerts, stats) | 5 |
| Trucks CRUD | 2 |
| Trips CRUD + dashboard | 3 |
| Alerts + filters | 4 |
| GPS Logs | 2 |
| Admin Panel (dashboard, companies, users, alerts) | 4 |
| Perception Agent (YOLO inference, edge cases) | 3 |
| Behaviour Analysis (normal, loitering, empty, missing) | 4 |
| Decision Engine (LOW/MED/HIGH/CRITICAL rules + validation) | 5 |
| Digital Twin (normal, anomalous, defaults) | 3 |
| Route Agent (Delhi, Mumbai, missing coords) | 3 |
| Risk Fusion (LOW, HIGH, empty signals) | 3 |
| Explainability (CRITICAL, empty payloads) | 2 |
| Vision Event (person, vehicle, missing trip) | 3 |
| Fusion Risk GET (valid, missing trip) | 2 |
| Simulation demo | 2 |
| Unauthenticated access (all should 401) | 5 |
| **TOTAL** | **59** |

Expected output on success:
```
════════════════════════════════════════════════════════════
  TEST SUMMARY
════════════════════════════════════════════════════════════
  PASSED : 59
  FAILED : 0
════════════════════════════════════════════════════════════

  🎉 All tests passed!
```

---

## 🔑 Quick Reference: All Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register-company/` | ❌ | Public company + user signup |
| POST | `/auth/login/` | ❌ | Get auth token |
| POST | `/auth/logout/` | ✅ | Invalidate token |
| GET | `/auth/me/` | ✅ | Current user profile |
| POST | `/auth/change-password/` | ✅ | Change password |
| POST | `/auth/register/` | ✅ Admin | Create company user |
| GET/POST | `/companies/` | ✅ | List / create companies |
| GET/PATCH/DELETE | `/companies/{id}/` | ✅ | Company detail |
| GET | `/companies/{id}/trucks/` | ✅ | Company trucks |
| GET | `/companies/{id}/alerts/` | ✅ | Company alerts |
| GET | `/companies/{id}/stats/` | ✅ | Company statistics |
| GET/POST | `/trucks/` | ✅ | List / create trucks |
| GET/PATCH/DELETE | `/trucks/{id}/` | ✅ | Truck detail |
| GET/POST | `/trips/` | ✅ | List / create trips |
| GET/PATCH/DELETE | `/trips/{id}/` | ✅ | Trip detail |
| GET | `/trips/{id}/dashboard/` | ✅ | Live trip dashboard |
| GET/POST | `/gps-logs/` | ✅ | List / log GPS positions |
| GET/POST | `/alerts/` | ✅ | List / create alerts |
| POST | `/alerts/{id}/resolve/` | ✅ | Mark alert resolved |
| POST | `/alerts/{id}/resend_notifications/` | ✅ | Resend SMS/email |
| GET | `/admin/dashboard/` | ✅ Admin | Platform-wide stats |
| GET | `/admin/companies/` | ✅ Admin | All companies |
| GET | `/admin/users/` | ✅ Admin | All users |
| GET/PATCH/DELETE | `/admin/users/{pk}/` | ✅ Admin | User management |
| GET | `/admin/alerts/` | ✅ Admin | All alerts |
| POST | `/agents/perception/` | ✅ | YOLO + DeepSort inference |
| POST | `/agents/behaviour-analysis/` | ✅ | IsolationForest anomaly detection |
| POST | `/agents/digital-twin/` | ✅ | IoT telemetry validation |
| POST | `/agents/route/` | ✅ | Shapely geofencing |
| POST | `/agents/risk-fusion/` | ✅ | Weighted risk aggregation |
| POST | `/agents/decision/` | ✅ | Rule engine + alert actions |
| POST | `/agents/explain/` | ✅ | LLM explanation generation |
| POST | `/agents/vision-event/` | ✅ | Legacy CV bridge |
| GET | `/agents/fusion-risk/` | ✅ | Legacy risk aggregation |
| POST | `/agents/simulate/` | ✅ | Full demo scenario |
