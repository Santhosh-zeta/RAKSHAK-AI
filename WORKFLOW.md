# RAKSHAK AI - Backend Workflow Document & Database Design

## 1. Database Design (PostgreSQL / SQLite for Hackathon)

The central piece of the intelligence system requires a robust relational database.

### 1.1 Tables Schema

**Table: `Trucks`**
- `truck_id` (UUID/String, Primary Key)
- `driver_name` (String)
- `cargo_type` (String)
- `cargo_value` (Decimal/Float)
- `created_at` (Datetime)

**Table: `Trips`**
- `trip_id` (UUID, Primary Key)
- `truck_id` (Foreign Key -> `Trucks.truck_id`)
- `start_location` (String/GeoJSON)
- `destination_location` (String/GeoJSON)
- `start_time` (Datetime)
- `estimated_arrival` (Datetime)
- `status` (String - Pending, In-Transit, Completed)

**Table: `GPSLogs`**
- `log_id` (UUID, Primary Key)
- `trip_id` (Foreign Key -> `Trips.trip_id`)
- `latitude` (Float)
- `longitude` (Float)
- `speed` (Float)
- `timestamp` (Datetime)

**Table: `Alerts`**
- `alert_id` (UUID, Primary Key)
- `trip_id` (Foreign Key -> `Trips.trip_id`)
- `type` (String - Vision, Behavior, Route, System)
- `risk_score` (Float)
- `description` (Text)
- `timestamp` (Datetime)

---

## 2. Development Workflow

### Phase 1: Foundation & APIs
1. **Repository Setup:** Structure the backend exactly as defined in the requirements inside a `backend/` folder.
2. **Environment & Django Setup:** Install Django, Django REST Framework, and setup `rakshak` base settings.
3. **Database Models:** Implement the Django ORM models corresponding to the Schema in the `surveillance/models.py`.
4. **CRUD Endpoints:** Build the DRF serializers and viewsets for Trucks, Trips, and GPS/Alerts data ingestion.

### Phase 2: Agent Architecture (LangGraph + AI)
1. **Agent Scaffolding:** Create the multi-agent files (`behavior_agent.py`, `route_agent.py`, etc.) with dummy or rule-based logic initially.
2. **Risk Fusion Engine:** Build the `risk_fusion_agent.py` to compile scores from all other agents and determine overall Risk Level.
3. **Decision & Action:** Build `decision_agent.py` to trigger notification rules based on fusion risk output.
4. **LLM Explanations:** Incorporate `explainability_agent.py` using LLM service wrappers to translate risk metrics into human-readable alerts.

### Phase 3: External Services & Integration
1. **Mock Endpoints/Services:** Create mock ML model integration layer in `ai_models/` and `train_models/`.
2. **External API Calls:** In `services/`, stub out Twilio (SMS), Map endpoints, and Language Model interfaces.
3. **Demo Scenario Setup:** Build an endpoint that simulates a trip and increments risk iteratively, logging to GPSLogs and generating Alerts to simulate the "Truck moves on map -> Person detected -> Risk increases" workflow.

---

I will now begin Phase 1 by generating the exact folder and file structure you requested for the backend.
