# RAKSHAK AI — Project Workflow Guide

This document is the single source of truth for running, understanding, and developing the RAKSHAK AI platform. Follow it in sequence. By the end, you will have both services live with a clear picture of what each part of the system is doing.

---

## Prerequisites

Before you begin, ensure the following are installed:

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| Node.js | 18.17+ | Frontend compiler |
| Git | Any | Version control |
| pip / venv | Bundled with Python | Python package management |
| npm | Bundled with Node | Frontend package management |

---

## Step 1 — Clone and Navigate

```bash
git clone <your-repo-url>
cd RAKSHAK-AI
```

You will see three top-level directories:

```
RAKSHAK-AI/
├── backend/          # Django REST Framework + AI agent system
├── frontend/         # Next.js 16 command center UI
└── AI-models/        # Trained .pkl model files (loaded by agents)
```

---

## Step 2 — Configure the Backend

### 2a. Create and activate a Python virtual environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2b. Create the backend environment file

Create a file called `.env` inside the `backend/` directory. A template is provided below — the defaults work for a local dev setup without Redis or external services.

```env
# Django
SECRET_KEY=replace-with-a-real-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database — leave blank to use SQLite (default for local dev)
DATABASE_URL=

# Redis — leave blank if not running Redis locally (agents degrade gracefully)
REDIS_URL=redis://localhost:6379

# Optional: OpenAI API key for the Explainability Agent
OPENAI_API_KEY=

# Optional: Twilio credentials for SMS alerts (can be left blank for demo mode)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

> **Note:** If `DATABASE_URL` is blank, Django falls back to the included `db.sqlite3` file automatically.
> If `REDIS_URL` is unreachable, the Vision, Behaviour, Digital Twin, and Route agents will run without pub/sub and simply log a warning.

### 2c. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs Django, DRF, LangGraph, PyTorch (CPU), YOLOv8 (Ultralytics), Scikit-Learn, OpenCV, Shapely, Twilio, and all other runtime dependencies.

**What is being installed and why:**

| Package | Role |
|---|---|
| `django`, `djangorestframework` | HTTP API server and serialization |
| `django-cors-headers` | Allows the Next.js frontend to call the API |
| `ultralytics` (YOLOv8) | Computer vision — person/object detection |
| `deep-sort-realtime` | Multi-object tracking layered on YOLO output |
| `torch`, `torchvision` | Neural net runtime (CPU build) |
| `scikit-learn` | IsolationForest for the Behaviour Agent |
| `shapely` | Geofence polygon checks in the Route Agent |
| `langgraph`, `langchain-core` | Multi-agent orchestration framework |
| `openai` | Explainability Agent LLM interface |
| `twilio` | SMS/call notifications for critical alerts |
| `redis` | Async pub/sub channel between agents |

### 2d. Create the database schema

```bash
python manage.py makemigrations
python manage.py migrate
```

This creates the SQLite tables: `Trucks`, `Trips`, `GPSLogs`, and `Alerts`.

### 2e. Create an admin user (optional but recommended)

```bash
python manage.py createsuperuser
```

You can also use the pre-seeded token via `create_token.py` if admin credentials already exist:

```bash
python create_token.py
```

### 2f. Start the Django development server

```bash
python manage.py runserver
```

The API is now live at `http://localhost:8000/api/`. You can verify by opening:
- `http://localhost:8000/api/trucks/` — should return `[]` if no data, or a list if seeded
- `http://localhost:8000/api/alerts/` — same pattern

> Keep this terminal open. The backend must be running for the frontend to speak to it.

---

## Step 3 — Configure the Frontend

Open a **second** terminal and navigate to the frontend directory.

### 3a. Create the frontend environment file

Create a file called `.env.local` inside the `frontend/` directory:

```env
# Points the frontend at the local Django backend
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Set to "true" to skip the backend entirely and use hardcoded seed data
# Useful for UI development without a running backend
NEXT_PUBLIC_USE_MOCK=false
```

### 3b. Install Node dependencies

```bash
cd frontend
npm install
```

### 3c. Start the Next.js development server

```bash
npm run dev
```

The Command Center UI is now live at `http://localhost:3000`. Turbopack compiles the TypeScript incrementally, so the first load takes ~3 seconds.

---

## Step 4 — Verify the Connection

Open `http://localhost:3000`. The UI will:

1. Try `GET /api/trips/` on the backend.
2. If trips exist, map them onto the dashboard.
3. If the backend is unreachable or returns empty data, it silently falls back to 10 pre-seeded demo trucks covering real Indian logistics corridors.

You will always see a fully functional UI regardless of backend state. The browser console will print `[RAKSHAK] Backend unreachable — using seed data.` if the API is down.

---

## Step 5 — Understand the Data Flow

### When the Dashboard Loads

```
Browser → GET /api/trips/
        → For each trip: GET /api/trips/{id}/dashboard/
        → Renders fleet map + telemetry grid
```

### When an Alert is Generated

```
IoT Device / Simulation → POST /api/gps-logs/     (speed, GPS, engine)
                        → POST /api/agents/digital-twin/   (weight, door state)
                        → POST /api/agents/route/           (geofence check)
                        → POST /api/agents/perception/      (base64 frame → YOLO)
                        → POST /api/agents/behaviour-analysis/ (track dwell time)
                        → All agents push risk_penalty scores to Risk Fusion
                        → Risk Fusion → Decision Agent → Alert created in DB
                        → Front-end polls GET /api/alerts/ every 30 seconds
                        → Alert appears in the Intelligence Center with AI explanation
```

### When Risk Analysis is Run (Pre-Journey)

```
User fills form (route, cargo, driver exp) →
    Frontend computes Bayesian score locally via riskUtils.ts →
    Optionally calls POST /api/agents/risk-fusion/ for live backend score →
    Displays animated gauge + breakdown report
```

---

## Step 6 — Running the Demo Simulation

The backend includes a demo endpoint that injects a scripted scenario — a truck stops unexpectedly, YOLO detects people near cargo doors, and the Decision Engine escalates to Critical.

First, create a trip in the admin panel or via the API:

```bash
# Replace {trip_id} with a real UUID from your database
curl -X POST http://localhost:8000/api/agents/simulate/ \
  -H "Content-Type: application/json" \
  -d '{"trip_id": "{trip_id}"}'
```

The simulation endpoint will:
1. Create a `Behavior` alert (unscheduled stop > 15 minutes).
2. Create a `Vision` alert (multi-person detection near rear doors).
3. Create a `System` alert (Decision Engine locks the container and calls the driver).
4. Update the trip's status to `Alert`.
5. Fire an SMS via Twilio if credentials are configured.

Refresh the Alerts page in the UI — the three new alerts will appear in priority order within 30 seconds.

---

## Step 7 — Production Build

When you are ready to build optimized static assets:

```bash
cd frontend
npm run build
npm run start    # Serves the production build on port 3000
```

For the backend in production:

```bash
cd backend
python manage.py collectstatic
gunicorn rakshak.wsgi:application --bind 0.0.0.0:8000
```

---

## Architecture Reference

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx             Homepage
│   │   ├── dashboard/           Fleet Command Center
│   │   ├── live-monitoring/     Pre-journey risk report generator
│   │   ├── risk-analysis/       AI risk analysis with animated gauge
│   │   └── alerts/              Alert Intelligence Center
│   ├── services/
│   │   ├── apiClient.ts         All backend API calls (auth, agents, CRUD)
│   │   └── riskUtils.ts         Client-side Bayesian risk computation
│   └── components/              Shared UI components (map, nav, etc.)

backend/
├── surveillance/
│   ├── models.py                Truck, Trip, GPSLog, Alert ORM models
│   ├── views.py                 CRUD viewsets (trucks, trips, gps, alerts)
│   ├── agent_views.py           HTTP bridges into AI agents
│   ├── auth_views.py            Login, logout, register, me endpoints
│   ├── agents/                  Individual AI agent implementations
│   │   ├── perception_agent.py  YOLO + DeepSort computer vision
│   │   ├── behavior_agent.py    IsolationForest anomaly detection
│   │   ├── digital_twin_agent.py IoT telemetry deviation check
│   │   ├── route_agent.py       Shapely geofence patrol
│   │   ├── risk_fusion_agent.py Weighted score aggregator
│   │   └── decision_agent.py    Rule engine → alert + SMS trigger
│   └── services/
│       └── sms_service.py       Twilio SMS wrapper
```

---

## Common Issues

**"Backend unreachable" shown in browser console**
This is expected if the Django server is not running. Start it with `python manage.py runserver`. The UI degrades gracefully to seed data.

**`pip install` fails on `torch` or `ultralytics`**
PyTorch CPU builds are large (~200MB). If the download times out, run `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` separately first, then re-run `pip install -r requirements.txt`.

**`CORS` errors in the browser**
Ensure `django-cors-headers` is installed and `CORS_ALLOW_ALL_ORIGINS = True` is in `backend/rakshak/settings.py` during local development.

**Port already in use**
Django defaults to `:8000`. Next.js defaults to `:3000`. If either port is taken, use `python manage.py runserver 8001` or `npm run dev -- -p 3001` and update `.env.local` accordingly.
