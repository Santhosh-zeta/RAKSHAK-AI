# RAKSHAK AI — Complete Frontend & Backend Workflow Guide

> **Single source of truth** for running, understanding, and developing the full RAKSHAK AI platform — from first `git clone` to a live login session with all 7 AI agents operational.

---

## 📦 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Backend Setup & Run](#3-backend-setup--run)
4. [Frontend Setup & Run](#4-frontend-setup--run)
5. [Login & Registration Workflow](#5-login--registration-workflow)
6. [Full Frontend UI Workflow](#6-full-frontend-ui-workflow)
7. [Full Backend API Workflow](#7-full-backend-api-workflow)
8. [AI Agent Pipeline — Step by Step](#8-ai-agent-pipeline--step-by-step)
9. [Demo Simulation](#9-demo-simulation)
10. [Production Build](#10-production-build)
11. [Architecture Reference](#11-architecture-reference)
12. [Common Issues & Fixes](#12-common-issues--fixes)

---

## 1. Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| Node.js | 18.17+ | Frontend compiler |
| Git | Any | Version control |
| pip / venv | Bundled with Python | Python package management |
| npm | Bundled with Node | Frontend package management |
| Redis *(optional)* | 6+ | Real-time agent pub/sub (falls back gracefully) |

---

## 2. Project Structure

```
RAKSHAK-AI/
├── backend/               # Django REST Framework + AI multi-agent system
│   ├── surveillance/
│   │   ├── agents/        # 7 AI agent implementations
│   │   ├── agent_views.py # HTTP bridges for each agent
│   │   ├── auth_views.py  # Auth: login, register, logout, me
│   │   ├── views.py       # CRUD: trucks, trips, gps, alerts
│   │   └── models.py      # ORM models
│   ├── rakshak/           # Django settings, URL routing
│   ├── requirements.txt
│   ├── manage.py
│   ├── create_token.py    # Quick token generator for testing
│   ├── test_all_apis.py   # 59-test automated API test suite
│   └── API_REFERENCE.md   # Full API documentation
│
├── frontend/              # Next.js 16 + TypeScript Command Center UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Landing / home page
│   │   │   ├── login/               # Login + Company Registration page
│   │   │   ├── dashboard/           # Fleet Command Center (live map + alerts)
│   │   │   ├── live-monitoring/     # Pre-journey risk report
│   │   │   ├── risk-analysis/       # AI risk analysis with animated gauge
│   │   │   └── alerts/              # Alert Intelligence Center
│   │   ├── context/
│   │   │   └── AuthContext.tsx      # Global auth state (token, user, company)
│   │   ├── services/
│   │   │   ├── apiClient.ts         # All backend API calls + auth headers
│   │   │   └── riskUtils.ts         # Client-side Bayesian risk computation
│   │   └── components/
│   │       ├── Navbar.tsx           # Nav with user dropdown + logout
│   │       └── MapView.tsx          # SVG India fleet tracking map
│   └── .env.local
│
└── AI-models/             # Trained .pkl model files loaded by agents
    └── behavior_model.pkl # IsolationForest (Behaviour Agent)
```

---

## 3. Backend Setup & Run

Open **Terminal 1** and follow these steps once:

### Step 3.1 — Navigate and create virtualenv

```bash
cd RAKSHAK-AI/backend
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

### Step 3.2 — Install dependencies

```bash
pip install -r requirements.txt
```

**What's being installed:**

| Package | Agent / Purpose |
|---|---|
| `django`, `djangorestframework` | API server and serialization |
| `django-cors-headers` | Allows the Next.js frontend to call the API from `:3000` |
| `ultralytics` (YOLOv8) | Perception Agent — person/object detection |
| `deep-sort-realtime` | Perception Agent — multi-object tracker on top of YOLO |
| `torch`, `torchvision` | Neural net runtime (CPU build) |
| `scikit-learn` | Behaviour Agent — IsolationForest anomaly detection |
| `shapely` | Route Agent — geofence polygon intersection |
| `redis` (asyncio) | Inter-agent pub/sub channels |
| `openai` | Explainability Agent — LLM text generation |
| `twilio` | Decision Agent — SMS alerts on CRITICAL events |

### Step 3.3 — Configure environment variables

Create `backend/.env` (these are the minimal defaults for local dev):

```env
SECRET_KEY=replace-with-a-real-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=          # blank = SQLite (auto-created)
REDIS_URL=redis://localhost:6379   # agents degrade gracefully if unreachable

OPENAI_API_KEY=        # blank = template-based explainer
LLM_PROVIDER=template  # options: openai | ollama | template

TWILIO_ACCOUNT_SID=    # blank = SMS suppressed (demo mode)
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

TRUCK_ID=TRK-001
```

### Step 3.4 — Create database schema

```bash
python manage.py migrate
```

Creates SQLite tables: `LogisticsCompany`, `CompanyUser`, `Truck`, `Trip`, `GPSLog`, `Alert`.

### Step 3.5 — Create admin user

```bash
python manage.py createsuperuser
# → username: admin
# → email: admin@rakshak.ai
# → password: Rakshak@123
```

Or generate a token directly for an existing admin:

```bash
python create_token.py
# → Token: 786c760b7a6684303cb9ab4286699d22a242ae73
```

### Step 3.6 — Start the backend server

```bash
python manage.py runserver 8000
```

**What happens when you run this:**
1. Django loads `rakshak/settings.py` — registers all apps and middleware
2. `StatReloader` watches all `.py` files and auto-restarts on changes
3. CORS headers are enabled — allows `localhost:3000` to call the API
4. The DRF Token auth system is active — all protected endpoints require `Authorization: Token <token>`
5. API is live at `http://localhost:8000/api/`

✅ **Verify backend is running:**
```bash
curl http://localhost:8000/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Rakshak@123"}'
# → Should return {"token":"...","user":{...},"company":null}
```

> **Keep Terminal 1 open.** The backend must stay running.

---

## 4. Frontend Setup & Run

Open **Terminal 2:**

### Step 4.1 — Navigate to frontend

```bash
cd RAKSHAK-AI/frontend
```

### Step 4.2 — Create environment file

```env
# frontend/.env.local

# Points the Next.js app at the local Django backend
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Set to "true" to skip backend entirely and use hardcoded seed data
# Useful for pure UI development without a running backend
NEXT_PUBLIC_USE_MOCK=false
```

### Step 4.3 — Install Node dependencies

```bash
npm install
```

### Step 4.4 — Start the development server

```bash
npm run dev
```

**What happens when you run this:**
1. Next.js 16 (Turbopack) starts the dev server
2. All TypeScript files are type-checked incrementally
3. `AuthProvider` wraps the entire app — reads `rakshak_token` from `localStorage` on every page load
4. `Navbar` checks auth state — shows Sign In button if not logged in, user avatar + dropdown if logged in
5. App is live at `http://localhost:3000`

✅ **Verify frontend is running:** Open `http://localhost:3000` — the homepage or login page should appear.

---

## 5. Login & Registration Workflow

### 5.1 Open the Login Page

Navigate to: `http://localhost:3000/login`

The page has **two tabs**:
- **Sign In** — for existing users
- **Register Company** — new logistics company onboarding

### 5.2 Sign In (Existing Admin)

**What happens in the browser:**
1. Type username (`admin`) and password (`Rakshak@123`)
2. Click **Sign In**

**What happens in the code (step by step):**
1. `handleLogin()` in `login/page.tsx` fires
2. Calls `AuthContext.login(username, password)`
3. `AuthContext` sends: `POST http://localhost:8000/api/auth/login/`
4. **Backend** (`auth_views.py`): calls Django's `authenticate()` to verify credentials
5. If valid: returns `{ token: "786c...", user: { username, role, email }, company: null }`
6. `AuthContext` stores the token in `localStorage` as `rakshak_token`
7. Stores `{ username, role }` as `rakshak_user` in `localStorage`
8. Updates React state: `isAuthenticated = true`
9. `useEffect` in `login/page.tsx` detects `isAuthenticated` → router redirects to `/dashboard`
10. `Navbar` re-renders with user avatar, name, and role badge

### 5.3 Register a New Company

**What happens in the browser:**
1. Click the **Register Company** tab
2. Fill in: Company Name, City, First/Last Name, Email, Username, Password
3. Click **Create Company Account**

**What happens in the code (step by step):**
1. `handleRegister()` validates required fields client-side
2. Calls `AuthContext.registerCompany(payload)`
3. Sends: `POST http://localhost:8000/api/auth/register-company/`
4. **Backend** (`auth_views.py`):
   - Creates a `LogisticsCompany` record
   - Creates a Django `User` with given credentials
   - Creates a `CompanyUser` profile with `role = "company_user"`
   - Generates and returns an auth token
5. Same token-storage flow as login (steps 6–10 above)
6. User is now logged in and redirected to `/dashboard`

### 5.4 Session Persistence

- Token stored in `localStorage` survives page refreshes and browser restarts
- On every app load, `AuthContext` reads `rakshak_token` from `localStorage`
- If valid, user is kept logged in without re-entering credentials
- Token is invalidated server-side on logout (`POST /auth/logout/` deletes it from DB)

### 5.5 Logout

Click the user avatar in the Navbar → **Sign out**

**What happens:**
1. Calls `AuthContext.logout()`
2. `POST /api/auth/logout/` — backend deletes the token from DB
3. `localStorage` entries `rakshak_token` and `rakshak_user` are cleared
4. React state resets: `isAuthenticated = false`
5. Router pushes to `/login`

---

## 6. Full Frontend UI Workflow

### Page: `/` — Landing Page
- Static marketing page with Framer Motion animations
- Hero section with parallax effect and floating draggable cards
- Technology bento grid with spotlight hover effects
- **CTA buttons** → link to `/dashboard`

### Page: `/login` — Authentication
- Two-tab form: Sign In / Register Company
- Connects to `POST /api/auth/login/` and `POST /api/auth/register-company/`
- Token stored in `localStorage`, redirects to `/dashboard` on success

### Page: `/dashboard` — Fleet Command Center
**On load:**
1. `getFleetData()` → `GET /api/trips/` then `GET /api/trips/{id}/dashboard/` per trip
2. `getAlerts()` → `GET /api/alerts/`
3. SVG India map renders truck pins colored by risk level
4. Stats grid shows: active consignments, critical threats, total cargo value, avg risk gauge

**Polling:** Every 30 seconds (paused when tab is hidden via Visibility API)

**Demo Button:**
- Calls `POST /api/agents/simulate/` with the highest-risk trip's ID
- Injects 3 pre-built alerts (Behavior + Vision + System)
- Escalates trip status to `Alert`
- Re-fetches data after 1 second

### Page: `/live-monitoring` — Journey Report
- Pre-journey risk report form (route, cargo type, driver info)
- Client-side Bayesian risk score via `riskUtils.ts`
- Optionally calls `POST /api/agents/risk-fusion/` for live backend score
- Animated risk gauge + breakdown chart

### Page: `/risk-analysis` — AI Risk Analysis
- Deep-dive risk inputs for a specific trip
- Calls all AI agents in sequence (optional)
- Shows component-level score breakdown: Vision, Behaviour, Twin, Route

### Page: `/alerts` — Intelligence Center
- Live feed of all alerts sorted by severity and time
- Filters: All / Critical / High / Medium / Low
- Each alert shows: truck ID, type badge, risk score, AI explanation
- Calls `GET /api/alerts/?severity=Critical` etc.

---

## 7. Full Backend API Workflow

All protected endpoints require the header:
```
Authorization: Token <your_token>
Content-Type: application/json
```

### Auth Endpoints (Public)

| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/login/` | Login → returns token + user + company |
| POST | `/api/auth/register-company/` | Register new company + first user |
| POST | `/api/auth/logout/` | Invalidate token |
| GET | `/api/auth/me/` | Get current user profile |

### Core CRUD (Protected)

| Method | URL | Description |
|---|---|---|
| GET/POST | `/api/companies/` | List / create companies |
| GET | `/api/companies/{id}/trucks/` | Company's trucks |
| GET | `/api/companies/{id}/stats/` | Dashboard statistics |
| GET/POST | `/api/trucks/` | List / create trucks |
| GET/POST | `/api/trips/` | List / create trips |
| GET | `/api/trips/{id}/dashboard/` | Live trip dashboard |
| GET/POST | `/api/gps-logs/` | List / log GPS positions |
| GET/POST | `/api/alerts/` | List / create alerts |
| POST | `/api/alerts/{id}/resolve/` | Resolve alert |

### Admin Panel (Admin role only)

| Method | URL | Description |
|---|---|---|
| GET | `/api/admin/dashboard/` | Platform-wide stats |
| GET | `/api/admin/companies/` | All companies |
| GET | `/api/admin/users/` | All users |

---

## 8. AI Agent Pipeline — Step by Step

Run these in order to simulate one complete cargo security cycle:

```
Camera / IoT Input
       │
       ▼
[1] POST /api/agents/perception/        ← YOLO + DeepSort → detects persons, assigns track IDs
       │
       ▼
[2] POST /api/agents/behaviour-analysis/ ← IsolationForest → loitering score, anomaly flag
       │
       ├── [3] POST /api/agents/digital-twin/  ← IoT validation: door, RFID, weight, signal
       │
       ├── [4] POST /api/agents/route/         ← Shapely geofence: safe corridor + risk zone check
       │
       ▼
[5] POST /api/agents/risk-fusion/       ← Weighted aggregation of all 3 scores → composite score
       │
       ▼
[6] POST /api/agents/decision/          ← Rule engine: R001/R002/R003 → fires SMS/email if needed
       │
       ▼
[7] POST /api/agents/explain/           ← LLM generates human-readable explanation for the alert
       │
       ▼
Alert saved to DB → Frontend polls and displays it
```

### Agent 1 — Perception (YOLO + DeepSort)

```
POST /api/agents/perception/
{
  "trip_id":    "<uuid>",
  "truck_id":   "TRK-001",
  "frame_id":   42,
  "frame_b64":  "<base64 JPEG>"
}
```

Internally: decodes image → YOLOv8 detects objects → DeepSort assigns persistent track IDs → computes dwell time + velocity → returns tracks + scene_tags → publishes to Redis `rakshak.perception.output`

### Agent 2 — Behaviour (IsolationForest)

```
POST /api/agents/behaviour-analysis/
{
  "trip_id": "<uuid>",
  "truck_id": "TRK-001",
  "tracks": [{ "track_id": 1, "dwell_seconds": 65.0, "velocity": {"dx":0.1,"dy":0.05}, "confidence": 0.91 }]
}
```

Internally: extracts 11 features per track → runs `behavior_model.pkl` → normalizes to [0,1] → checks loitering (dwell > 30s), crowd anomaly (> 4 tracks) → creates alert if flagged

### Agent 3 — Digital Twin (IoT Validator)

```
POST /api/agents/digital-twin/
{
  "trip_id": "<uuid>", "truck_id": "TRK-001",
  "door_state": "OPEN", "cargo_weight_kg": 500.0,
  "engine_on": false, "driver_rfid_scanned": false,
  "gps_lat": 28.6139, "gps_lon": 77.2090,
  "iot_signal_strength": 0.15
}
```

Internally: runs 5 deviation checks (door+RFID, weight, GPS, engine, signal) → scores each → computes NOMINAL / DEGRADED / CRITICAL status

### Agent 4 — Route (Shapely Geofencing)

```
POST /api/agents/route/
{
  "trip_id": "<uuid>", "truck_id": "TRK-001",
  "gps_lat": 28.8500, "gps_lon": 77.0900
}
```

Internally: `Point(lon, lat)` tested against safe corridor polygons + high-risk zone polygons → time-of-day multiplier (night = ×2.0) → returns `in_safe_corridor`, `in_high_risk_zone`, `route_risk_score`

### Agent 5 — Risk Fusion (Weighted Aggregator)

```
POST /api/agents/risk-fusion/
{
  "trip_id": "<uuid>", "truck_id": "TRK-001",
  "behaviour": { "anomaly_score": 0.78, "loitering_detected": true },
  "twin":      { "deviation_score": 0.82, "door_state": "OPEN" },
  "route":     { "route_risk_score": 0.72, "in_high_risk_zone": true }
}
```

Internally: quality-adjusted weights (behaviour=35%, twin=30%, route=25%, temporal=10%) → composite score → triggered rule classification → updates `trip.current_calculated_risk` in DB

### Agent 6 — Decision (Rule Engine)

```
POST /api/agents/decision/
{
  "trip_id": "<uuid>", "truck_id": "TRK-001",
  "composite_risk_score": 0.77, "risk_level": "HIGH",
  "triggered_rules": ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID"]
}
```

Internally:
- R001 (score ≥ 0.85 → CRITICAL): SMS + email + log
- R002 (0.65–0.84 → HIGH): email + log
- R003 (0.45–0.64 → MEDIUM): log only
- Cooldown checked via Redis key `alert_cooldown:{truck_id}:{rule_id}` to prevent spam

### Agent 7 — Explainability (LLM / Template)

```
POST /api/agents/explain/
{
  "trip_id": "<uuid>",
  "risk_payload": { ... },
  "decision_payload": { "rule_name": "HIGH_RISK_ALERT", "actions_taken": ["email"] }
}
```

Internally: builds structured prompt → sends to OpenAI/Ollama (if configured) or falls back to rule-based template → saves text to `alert.ai_explanation` in DB

---

## 9. Demo Simulation

One-shot endpoint to inject a full threat scenario without calling each agent manually:

```bash
curl -X POST http://localhost:8000/api/agents/simulate/ \
  -H "Authorization: Token <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"trip_id": "<uuid>"}'
```

**What it does:**
1. Creates `Behavior` alert (risk 35%) — unscheduled stop
2. Creates `Vision` alert (risk 45%) — multi-person detection near cargo doors
3. Creates `System` alert (risk 80%) — Decision Engine critical action
4. Sets trip `status = Alert`
5. Fires SMS via Twilio if credentials are configured

The Dashboard's **🚨 Trigger Demo** button does this automatically using the highest-risk trip in the current fleet.

---

## 10. Production Build

### Frontend

```bash
cd frontend
npm run build       # TypeScript compile + static optimization
npm run start       # Serve production build on :3000
```

### Backend

```bash
cd backend
python manage.py collectstatic
gunicorn rakshak.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Automated Test Suite (59 tests)

```bash
# Backend must be running first
cd backend && source venv/bin/activate
python test_all_apis.py
# Expected: PASSED: 59 / FAILED: 0
```

---

## 11. Architecture Reference

```
┌────────────────────────── FRONTEND (Next.js 16) ──────────────────────────┐
│                                                                             │
│  AuthContext (localStorage token) ──→ Navbar (avatar + logout)             │
│         │                                                                   │
│  /login ──── POST /auth/login/  ──────────────────────────────────────┐   │
│         │    POST /auth/register-company/                               │   │
│         │                                                               │   │
│  /dashboard                                                             │   │
│    ├── GET /trips/ + /trips/{id}/dashboard/  →  Map + Stats Grid        │   │
│    ├── GET /alerts/                          →  Threat Feed             │   │
│    └── POST /agents/simulate/                →  Demo Scenario           │   │
│                                                                         │   │
│  /alerts   → GET /alerts/?severity=Critical                             │   │
│  /live-monitoring  → POST /agents/risk-fusion/                          │   │
│  /risk-analysis    → POST /agents/perception/ + behaviour + decision    │   │
│                                                                         │   │
└─────────────────────────────────────────────────────────────────────────│──┘
                  All calls include: Authorization: Token <token>          │
                  ↕ HTTP/JSON                                              │
┌────────────────────────── BACKEND (Django 6 / DRF) ─────────────────────│──┐
│                                                                          │   │
│  auth_views.py   ←── /auth/login|logout|register-company|me  ←──────────┘   │
│  views.py        ←── /trucks|trips|gps-logs|alerts|companies                │
│  agent_views.py  ←── /agents/perception|behaviour|twin|route|decision|...   │
│                                                                              │
│  ┌── PerceptionAgent  ── YOLOv8 + DeepSort ─────────────────┐              │
│  ├── BehaviourAgent   ── IsolationForest (behavior_model.pkl) │  Redis      │
│  ├── DigitalTwinAgent ── IoT deviation scoring                │  Pub/Sub    │
│  ├── RouteAgent       ── Shapely geofence polygons            │  (optional) │
│  ├── RiskFusionAgent  ── Weighted/Bayesian aggregator         │             │
│  ├── DecisionAgent    ── Rule engine → Twilio SMS             │             │
│  └── ExplainAgent     ── OpenAI / Ollama / Template LLM ─────┘             │
│                                                                              │
│  models.py: LogisticsCompany → CompanyUser → Truck → Trip → Alert           │
│  db.sqlite3 / PostgreSQL                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Common Issues & Fixes

### "Backend unreachable" in browser console
The Django server is not running. Start it with:
```bash
cd backend && source venv/bin/activate && python manage.py runserver 8000
```

### Port already in use
```bash
# Find and kill whatever is on port 8000:
fuser -k 8000/tcp
# Then restart the server
```

### Login throws 401 even with correct password
Reset the admin password:
```bash
python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.get(username='admin'); u.set_password('Rakshak@123'); u.save()"
```

### `pip install` fails on `torch`
PyTorch CPU builds are ~200MB. Install it separately first:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### CORS errors in browser
Verify `CORS_ALLOW_ALL_ORIGINS = True` in `backend/rakshak/settings.py` and that `corsheaders` is in `INSTALLED_APPS`.

### Frontend shows seed data instead of real backend data
Check that `NEXT_PUBLIC_USE_MOCK=false` in `frontend/.env.local` and that the backend is running. The browser console will show `[RAKSHAK] Backend unreachable — using seed data.` if the API is down.

### "Event loop is closed" error in agent endpoints
All agent views now use the `run_async()` helper which creates a fresh event loop per request. If you see this, ensure you are running the latest `surveillance/agent_views.py` from this repo.

### Frontend login doesn't redirect after sign in
Check that the backend `POST /api/auth/login/` returns `{"token": "...", "user": {...}}`. The frontend `AuthContext` reads `data.token` (DRF format). If your backend returns JWT (`data.access`), the fallback `data.access ?? data.token` handles both.
