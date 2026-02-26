# RAKSHAK AI — Backend Gaps & Recommendations
> This document lists what is ALREADY DONE in the backend, what is MISSING vs the spec,
> and recommended additions. **No code changes are made automatically — discuss with team first.**

---

## ✅ WHAT IS ALREADY IMPLEMENTED

| Module (from spec) | Backend Status |
|---|---|
| Theft Prediction Engine | ✅ `risk_fusion_agent.py` — weighted + Bayesian fusion. `risk_model.pkl` trained |
| Vision AI Detection (YOLOv8) | ✅ `perception_agent.py` — YOLO + DeepSORT, REST bridge via `/api/agents/perception/` |
| Behavior Intelligence Engine | ✅ `behavior_agent.py` — IsolationForest, loitering/crowd detection, `behavior_model.pkl` |
| Digital Twin Engine | ✅ `digital_twin_agent.py` — IoT telemetry, deviation detection, Redis pub/sub |
| Explainable Risk Engine | ✅ `explainability_agent.py` — rule-based scoring + explanation generation |
| Route Risk Intelligence | ✅ `route_agent.py` — Shapely geofencing, safe corridors, risk zones, `route_model.pkl` |
| Decision Engine | ✅ `decision_agent.py` — Rules R001/R002/R003, cooldown, Redis logging |
| Orchestrator | ✅ `orchestrator.py` — ties agents together |
| Django Models | ✅ `LogisticsCompany`, `Truck`, `Trip`, `GPSLog`, `Alert`, `ControlAreaContact`, `CompanyUser` |
| REST API | ✅ All agent views bridged via DRF: perception, behaviour, decision, digital-twin, route, risk-fusion |
| Notifications | ✅ `notification_service.py` — email + SMS (Twilio), `sms_service.py` |
| Auth | ✅ Token auth, role-based (admin / company_user / viewer) |
| Demo Simulation | ✅ `/api/agents/simulate/` endpoint injects sample alerts for demo |

---

## ⚠️ GAPS / MISSING vs SPEC

### 1. Pre-Journey Risk Report (Module 7 in spec)
- **Spec says**: Generate a full risk report *before* the journey starts — route, danger zones, recommendations.
- **Current state**: No dedicated `/api/reports/pre-journey/` endpoint. `risk_fusion_agent` scores in real-time but no static report saved to DB.
- **Recommendation**: Add a `JourneyReport` model and a `POST /api/trips/{id}/pre-journey-report/` endpoint that calls the route agent + risk fusion and saves a snapshot.

### 2. GPS Log Ingestion (Real-time Streaming)
- **Spec says**: GPS logs are continuously ingested.
- **Current state**: `GPSLog` model exists, `simulate_truck.py` script exists, but no authenticated WebSocket or polling endpoint for *real trucks to push GPS in real time*.
- **Recommendation**: Add `POST /api/trips/{id}/gps/` that accepts lat/lng/speed and saves a `GPSLog` row (already modeled). This feeds real-time map tracking.

### 3. Risk Score Stored on Trip (Live Updates)
- **Current state**: `Trip.current_calculated_risk` field exists but is only updated manually when alerts fire.
- **Recommendation**: Auto-update `current_calculated_risk` each time a new GPS log or alert is created, by calling the risk fusion agent in a signal or background task.

### 4. Driver Email Notifications
- `Truck.driver_email` field exists. `notification_service.py` is implemented.
- **Gap**: Driver email is never called from the decision agent or alert flows — only control room contacts are notified.
- **Recommendation**: When `severity = Critical`, also fire `notification_service.send_email(driver_email, ...)`.

### 5. Route Risk Intelligence Map Data (Public API)
- **Spec says**: Map should show Safe (green) / Medium (yellow) / High (red) zones via Leaflet.
- **Current state**: `route_agent.py` has zone polygons internally, but no public API endpoint exposes zone GeoJSON for the frontend map.
- **Recommendation**: Add `GET /api/route-zones/` that returns zone GeoJSON so the frontend Leaflet map can render colored overlays.

### 6. LLM/Explainability Service
- `llm_service.py` exists but appears empty (0 bytes). 
- `explainability_agent.py` is implemented with rule-based scoring.
- **Recommendation**: Wire `explainability_agent.py` into the alert creation flow so `Alert.ai_explanation` is always populated with human-readable explanations.

### 7. Supabase Integration
- `supabase_service.py` exists but appears empty (0 bytes).
- **Recommendation**: Either implement or remove so it doesn't confuse the codebase.

### 8. WebSocket / SSE for Real-Time Dashboard
- **Current state**: Frontend polls every N seconds. No push mechanism.
- **Recommendation**: Add Django Channels + WebSocket endpoint so alerts are pushed to the dashboard in real-time. (This is a significant addition — Phase 2.)

---

## 🏗️ NICE-TO-HAVE (Future, not Critical for Hackathon)

- `GET /api/trucks/{id}/digital-twin-profile/` — expose the Digital Twin's learned baseline for a truck
- Batch GPS ingest endpoint for simulating historical replay
- Admin panel for creating demo scenarios without needing the API
- Rate limiting on agent views to prevent overload

---

> For hackathon, the **3 most impactful additions** are:
> 1. `POST /api/trips/{id}/gps/` — real GPS ingestion
> 2. `GET /api/route-zones/` — zone GeoJSON for map
> 3. Wire explainability agent to alert creation
