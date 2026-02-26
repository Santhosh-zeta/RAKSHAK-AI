# RAKSHAK-AI Backend — Step-by-Step API Guide

This guide walks you through using the RAKSHAK-AI Backend APIs, mapping out a full workflow from authentication to executing the multi-agent cargo security pipeline.

---

## Step 1: Postman Environment Setup

Before calling the APIs, set up your environment variables in Postman to easily reuse values across different requests.

1. **Create a new Environment** in Postman and add these variables:
   - `base_url`: `http://127.0.0.1:8000/api`
   - `token`: *(Leave blank for now, we will fill this in Step 2)*
   - `trip_id`: *(Leave blank for now)*
   - `truck_id`: *(Leave blank for now)*

2. **Configure Authentication:**
   For **every** request starting from Step 3, go to the **Headers** tab and add:
   - `Authorization`: `Token {{token}}`
   - `Content-Type`: `application/json`

*(Alternatively, for local testing, you can generate a master admin token by running `python create_token.py` in your backend directory and skip Step 2).*

---

## Step 2: Registration & Authentication

You need an active user and an authorization token to interact with the system.

### Option A: Register a New Logistics Company (Public)
Creates a new company and automatically registers the first user as its administrator.
- **Method:** `POST`
- **URL:** `{{base_url}}/auth/register-company/`
- **Body (JSON):**
  ```json
  {
    "company_name": "NextGen Logistics",
    "company_city": "Delhi",
    "username": "admin_nextgen",
    "password": "SecurePassword123",
    "email": "ops@nextgen.com",
    "first_name": "Raj",
    "last_name": "Kumar"
  }
  ```
- **Action:** Copy the `token` from the response and paste it into your Postman Environment `token` variable.

### Option B: Login Existing User
- **Method:** `POST`
- **URL:** `{{base_url}}/auth/login/`
- **Body (JSON):**
  ```json
  {
    "username": "admin_nextgen",
    "password": "SecurePassword123"
  }
  ```

---

## Step 3: Fetch Base Resources

Verify that the system is properly seeded by retrieving the active Trucks and Trips.

### 3.1 List Trucks
- **Method:** `GET`
- **URL:** `{{base_url}}/trucks/`
- **Action:** Find an active truck and copy its ID into your Environment variable `truck_id` (e.g., `TRK-001`).

### 3.2 List Trips 
- **Method:** `GET`
- **URL:** `{{base_url}}/trips/`
- **Action:** Find a trip associated with your truck and copy its ID into your Environment variable `trip_id` (e.g., `ce6c07de-5060-4919-8bd6-69580cf1b3f8`).

---

## Step 4: The Full AI pipeline

To simulate a real cargo security event, execute the multi-agent pipeline in the exact order below. 

### 4.1 Perception Agent (Computer Vision)
Detects objects and people in a raw camera frame.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/perception/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
    "frame_id": 42,
    "frame_b64": "<base64_encoded_image_string>"
  }
  ```

### 4.2 Behaviour Analysis Agent
Analyzes the visual tracks to detect anomalous behavior like loitering near cargo.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/behaviour-analysis/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
    "tracks": [
      {
        "track_id": 1,
        "dwell_seconds": 65.0,
        "velocity": { "dx": 0.1, "dy": 0.05 },
        "confidence": 0.91
      }
    ]
  }
  ```
- **Expect:** Returns an `anomaly_score` based on `dwell_seconds` and movement.

### 4.3 Digital Twin Agent (IoT / Telemetry)
Evaluates physical vehicle state logic (doors, engine, RFID, signal strength).
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/digital-twin/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
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
- **Expect:** Captures logical violations like "Door is OPEN but RFID wasn't scanned".

### 4.4 Route Agent (Geofencing)
Checks GPS coordinates against high-risk zones and safe corridors.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/route/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
    "gps_lat": 28.8500,
    "gps_lon": 77.0900
  }
  ```
- *(Note: `28.8500, 77.0900` simulates being inside the Narela Industrial high-risk zone)*

### 4.5 Risk Fusion Agent
Aggregates the scores from Behaviour, Digital Twin, and Route agents to formulate a single composite risk state.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/risk-fusion/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
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
- **Action:** Note the `composite_risk_score` for the next step.

### 4.6 Decision Agent
Evaluates the rules against the generated composite score. If the risk is high enough (e.g., > 0.85), it triggers actions like SMS/Email alerts.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/decision/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
    "truck_id": "{{truck_id}}",
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

### 4.7 Explainability Agent
Translates raw alert metrics into a human-readable explanation using an LLM or template.
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/explain/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}",
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

---

## Step 5: Validating Output

Once the AI pipeline completes a cycle that yields a high risk score, an alert is securely generated.

### 5.1 Review Generated Alerts
- **Method:** `GET`
- **URL:** `{{base_url}}/alerts/`
- **Action:** Explore the response. You should see a new alert appended to the specific trip, containing the detailed `ai_explanation` and `risk_score` generated from Step 4.

---

## Optional Utilities

### Creating Live GPS Logs
If simulating a truck on a moving map interface:
- **Method:** `POST`
- **URL:** `{{base_url}}/gps-logs/`
- **Body (JSON):**
  ```json
  {
    "trip": "{{trip_id}}",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "speed": 60.5,
    "heading": 180.0,
    "timestamp": "2026-02-26T10:00:00Z"
  }
  ```

### Automated End-to-End Simulation
To run a predefined high-risk simulation instantly without calling all 7 agents manually:
- **Method:** `POST`
- **URL:** `{{base_url}}/agents/simulate/`
- **Body (JSON):**
  ```json
  {
    "trip_id": "{{trip_id}}"
  }
  ```
