#!/usr/bin/env python3
"""
RAKSHAK-AI — Comprehensive Backend & AI Agent API Test Suite
Tests ALL endpoints: Auth, CRUD, Admin Panel, and all 10 AI Agent endpoints.
Run: python test_all_apis.py
"""

import requests
import json
import base64
import sys
import time

BASE = "http://localhost:8000/api"

# ── Colours ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

passed = 0
failed = 0
warnings = 0

def ok(label, detail=""):
    global passed
    passed += 1
    print(f"  {GREEN}✓  PASS{RESET}  {label}" + (f"  {YELLOW}→ {detail}{RESET}" if detail else ""))

def fail(label, reason=""):
    global failed
    failed += 1
    print(f"  {RED}✗  FAIL{RESET}  {label}" + (f"  → {reason}" if reason else ""))

def warn(label, detail=""):
    global warnings
    warnings += 1
    print(f"  {YELLOW}⚠  WARN{RESET}  {label}" + (f"  → {detail}" if detail else ""))

def section(title):
    print(f"\n{CYAN}{BOLD}{'─'*60}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'─'*60}{RESET}")

def check(resp, label, expected_status, key=None):
    """Assert status code, optionally check a key exists in JSON response."""
    if resp.status_code == expected_status:
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass
        if key and key not in data:
            fail(label, f"Missing key '{key}' in response")
            return data
        detail = ""
        if data:
            # Show first meaningful field for context
            for k in ["token","message","trip_id","truck_id","risk_level","twin_status",
                       "composite_risk_score","explanation_text","rule_fired","is_anomaly",
                       "in_safe_corridor","count","id","alert_id","name"]:
                if k in data:
                    detail = f"{k}={json.dumps(data[k])[:60]}"
                    break
        ok(label, detail)
        return data
    else:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:120]
        fail(label, f"HTTP {resp.status_code} → {body}")
        return {}

# ── Tiny 1×1 JPEG in base64 (valid image for PerceptionAgent) ─────────────
# A real 1×1 white JPEG (ffd8...ffd9)
TINY_JPEG_BYTES = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e'
    b'C  C\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4'
    b'\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5'
    b'\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}'
    b'\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1'
    b'\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456'
    b'789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a'
    b'\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9'
    b'\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8'
    b'\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6'
    b'\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00'
    b'\x08\x01\x01\x00\x00?\x00\xfb\xd7\xff\xd9'
)
TINY_JPEG_B64 = base64.b64encode(TINY_JPEG_BYTES).decode()

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1 — AUTH
# ═══════════════════════════════════════════════════════════════════════════
section("1. AUTH ENDPOINTS")

# Login
r = requests.post(f"{BASE}/auth/login/", json={"username": "admin", "password": "Rakshak@123"})
data = check(r, "POST /auth/login/ (admin)", 200, "token")
TOKEN = data.get("token", "")
H = {"Authorization": f"Token {TOKEN}"}

if not TOKEN:
    print(f"\n{RED}Cannot continue without auth token — aborting.{RESET}")
    sys.exit(1)

# Me
r = requests.get(f"{BASE}/auth/me/", headers=H)
check(r, "GET  /auth/me/", 200)

# Bad login
r = requests.post(f"{BASE}/auth/login/", json={"username": "admin", "password": "WRONGPASS"})
check(r, "POST /auth/login/ (bad creds → 401)", 401)

# Missing fields
r = requests.post(f"{BASE}/auth/login/", json={"username": ""})
check(r, "POST /auth/login/ (missing fields → 400)", 400)

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2 — COMPANIES
# ═══════════════════════════════════════════════════════════════════════════
section("2. COMPANIES CRUD")

r = requests.get(f"{BASE}/companies/", headers=H)
companies = check(r, "GET  /companies/", 200)
company_list = companies if isinstance(companies, list) else companies.get("results", [])

COMPANY_ID = None
if company_list:
    COMPANY_ID = company_list[0].get("company_id")
    r = requests.get(f"{BASE}/companies/{COMPANY_ID}/", headers=H)
    check(r, f"GET  /companies/{COMPANY_ID[:8]}…/", 200)

    r = requests.get(f"{BASE}/companies/{COMPANY_ID}/trucks/", headers=H)
    check(r, f"GET  /companies/{COMPANY_ID[:8]}…/trucks/", 200)

    r = requests.get(f"{BASE}/companies/{COMPANY_ID}/alerts/", headers=H)
    check(r, f"GET  /companies/{COMPANY_ID[:8]}…/alerts/", 200)

    r = requests.get(f"{BASE}/companies/{COMPANY_ID}/stats/", headers=H)
    check(r, f"GET  /companies/{COMPANY_ID[:8]}…/stats/", 200)
else:
    warn("No companies found — some tests skipped")

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3 — TRUCKS
# ═══════════════════════════════════════════════════════════════════════════
section("3. TRUCKS CRUD")

r = requests.get(f"{BASE}/trucks/", headers=H)
trucks = check(r, "GET  /trucks/", 200)
truck_list = trucks if isinstance(trucks, list) else trucks.get("results", [])

TRUCK_UUID = None
if truck_list:
    TRUCK_UUID = truck_list[0].get("truck_id")
    r = requests.get(f"{BASE}/trucks/{TRUCK_UUID}/", headers=H)
    check(r, f"GET  /trucks/{TRUCK_UUID[:8]}…/", 200)

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 4 — TRIPS
# ═══════════════════════════════════════════════════════════════════════════
section("4. TRIPS CRUD")

r = requests.get(f"{BASE}/trips/", headers=H)
trips = check(r, "GET  /trips/", 200)
trip_list = trips if isinstance(trips, list) else trips.get("results", [])

TRIP_ID = None
if trip_list:
    TRIP_ID = trip_list[0].get("trip_id")
    r = requests.get(f"{BASE}/trips/{TRIP_ID}/", headers=H)
    check(r, f"GET  /trips/{TRIP_ID[:8]}…/", 200)

    r = requests.get(f"{BASE}/trips/{TRIP_ID}/dashboard/", headers=H)
    check(r, f"GET  /trips/{TRIP_ID[:8]}…/dashboard/", 200)
else:
    warn("No trips found — agent tests need a valid trip_id")

# Pick an "In-Transit" trip if possible so agent tests work better
for t in trip_list:
    if t.get("status") in ("In-Transit", "Alert"):
        TRIP_ID = t.get("trip_id")
        break

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 5 — ALERTS
# ═══════════════════════════════════════════════════════════════════════════
section("5. ALERTS CRUD")

r = requests.get(f"{BASE}/alerts/", headers=H)
check(r, "GET  /alerts/", 200)

r = requests.get(f"{BASE}/alerts/?severity=Critical", headers=H)
check(r, "GET  /alerts/?severity=Critical", 200)

r = requests.get(f"{BASE}/alerts/?resolved=false", headers=H)
check(r, "GET  /alerts/?resolved=false", 200)

if TRIP_ID:
    r = requests.get(f"{BASE}/alerts/?trip_id={TRIP_ID}", headers=H)
    check(r, f"GET  /alerts/?trip_id={TRIP_ID[:8]}…", 200)

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 6 — GPS LOGS
# ═══════════════════════════════════════════════════════════════════════════
section("6. GPS LOGS")

r = requests.get(f"{BASE}/gps-logs/", headers=H)
check(r, "GET  /gps-logs/", 200)

if TRIP_ID:
    r = requests.get(f"{BASE}/gps-logs/?trip_id={TRIP_ID}", headers=H)
    check(r, f"GET  /gps-logs/?trip_id={TRIP_ID[:8]}…", 200)

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 7 — ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════
section("7. ADMIN PANEL ENDPOINTS")

r = requests.get(f"{BASE}/admin/dashboard/", headers=H)
check(r, "GET  /admin/dashboard/", 200)

r = requests.get(f"{BASE}/admin/companies/", headers=H)
check(r, "GET  /admin/companies/", 200)

r = requests.get(f"{BASE}/admin/users/", headers=H)
check(r, "GET  /admin/users/", 200)

r = requests.get(f"{BASE}/admin/alerts/", headers=H)
check(r, "GET  /admin/alerts/", 200)

# ═══════════════════════════════════════════════════════════════════════════
#  SKIP if no trip is available
# ═══════════════════════════════════════════════════════════════════════════
if not TRIP_ID:
    print(f"\n{RED}No trip_id found — skipping all AI Agent tests{RESET}")
else:
    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 8 — AI AGENT: Perception (YOLO + DeepSort)
    # ═══════════════════════════════════════════════════════════════════════
    section("8. AI AGENT — Perception (YOLO + DeepSort)")
    print(f"  {YELLOW}Note: First call loads YOLO model (may take a few seconds){RESET}")

    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "frame_b64": TINY_JPEG_B64,
        "frame_id": 1
    }
    r = requests.post(f"{BASE}/agents/perception/", json=payload, headers=H, timeout=60)
    check(r, "POST /agents/perception/ (YOLO inference)", 200)

    # Missing frame
    r = requests.post(f"{BASE}/agents/perception/", json={"trip_id": TRIP_ID}, headers=H)
    check(r, "POST /agents/perception/ (missing frame → 400)", 400)

    # Bad trip
    r = requests.post(f"{BASE}/agents/perception/",
                      json={"trip_id": "00000000-0000-0000-0000-000000000000",
                            "frame_b64": TINY_JPEG_B64}, headers=H)
    check(r, "POST /agents/perception/ (invalid trip → 404)", 404)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 9 — AI AGENT: Behaviour Analysis (IsolationForest)
    # ═══════════════════════════════════════════════════════════════════════
    section("9. AI AGENT — Behaviour Analysis (IsolationForest ML Model)")

    # Normal behaviour
    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "tracks": [
            {"track_id": 1, "dwell_seconds": 5.0,  "velocity": {"dx": 1.0, "dy": 0.5}, "confidence": 0.7}
        ]
    }
    r = requests.post(f"{BASE}/agents/behaviour-analysis/", json=payload, headers=H)
    check(r, "POST /agents/behaviour-analysis/ (normal tracks)", 200)

    # Suspicious: long dwell + low velocity = loitering
    payload_suspicious = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "tracks": [
            {"track_id": 2, "dwell_seconds": 65.0, "velocity": {"dx": 0.1, "dy": 0.0}, "confidence": 0.92},
            {"track_id": 3, "dwell_seconds": 80.0, "velocity": {"dx": 0.0, "dy": 0.1}, "confidence": 0.85},
        ]
    }
    r = requests.post(f"{BASE}/agents/behaviour-analysis/", json=payload_suspicious, headers=H)
    check(r, "POST /agents/behaviour-analysis/ (loitering tracks)", 200)

    # Empty tracks
    r = requests.post(f"{BASE}/agents/behaviour-analysis/",
                      json={"trip_id": TRIP_ID, "tracks": []}, headers=H)
    check(r, "POST /agents/behaviour-analysis/ (empty tracks)", 200)

    # Missing trip
    r = requests.post(f"{BASE}/agents/behaviour-analysis/",
                      json={"tracks": []}, headers=H)
    check(r, "POST /agents/behaviour-analysis/ (missing trip → 400)", 400)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 10 — AI AGENT: Decision Engine
    # ═══════════════════════════════════════════════════════════════════════
    section("10. AI AGENT — Decision Engine (Rule Engine)")

    # Low risk → no rule fired
    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "composite_risk_score": 0.2,
        "risk_level": "LOW",
        "confidence": 0.9,
        "component_scores": {"vision": 0.1, "behaviour": 0.2},
        "triggered_rules": [],
        "fusion_method": "weighted_sum"
    }
    r = requests.post(f"{BASE}/agents/decision/", json=payload, headers=H)
    check(r, "POST /agents/decision/ (LOW risk → no rule)", 200)

    # Medium risk → R003
    payload["composite_risk_score"] = 0.55
    payload["risk_level"] = "MEDIUM"
    r = requests.post(f"{BASE}/agents/decision/", json=payload, headers=H)
    check(r, "POST /agents/decision/ (MEDIUM risk → R003)", 200)

    # High risk → R002
    payload["composite_risk_score"] = 0.75
    payload["risk_level"] = "HIGH"
    r = requests.post(f"{BASE}/agents/decision/", json=payload, headers=H)
    check(r, "POST /agents/decision/ (HIGH risk → R002)", 200)

    # Critical risk → R001 (escalates trip)
    payload["composite_risk_score"] = 0.92
    payload["risk_level"] = "CRITICAL"
    payload["triggered_rules"] = ["loitering", "night_activity"]
    r = requests.post(f"{BASE}/agents/decision/", json=payload, headers=H)
    check(r, "POST /agents/decision/ (CRITICAL risk → R001)", 200)

    # Out of range score
    payload["composite_risk_score"] = 1.5
    r = requests.post(f"{BASE}/agents/decision/", json=payload, headers=H)
    check(r, "POST /agents/decision/ (score > 1.0 → 400)", 400)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 11 — AI AGENT: Digital Twin
    # ═══════════════════════════════════════════════════════════════════════
    section("11. AI AGENT — Digital Twin (IoT Deviation Detector)")

    # Normal telemetry
    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "gps_lat": 28.6139, "gps_lon": 77.2090,
        "door_state": "CLOSED",
        "cargo_weight_kg": 1950.0,
        "engine_on": True,
        "driver_rfid_scanned": True,
        "iot_signal_strength": 0.95
    }
    r = requests.post(f"{BASE}/agents/digital-twin/", json=payload, headers=H)
    check(r, "POST /agents/digital-twin/ (normal telemetry)", 200)

    # Anomalous: door open, no RFID, weight mismatch
    payload_anomalous = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "gps_lat": 30.5, "gps_lon": 80.1,
        "door_state": "OPEN",
        "cargo_weight_kg": 500.0,    # big deviation from 2000kg baseline
        "engine_on": False,
        "driver_rfid_scanned": False,
        "iot_signal_strength": 0.1
    }
    r = requests.post(f"{BASE}/agents/digital-twin/", json=payload_anomalous, headers=H)
    check(r, "POST /agents/digital-twin/ (anomalous: door open + no RFID)", 200)

    # Missing gps coords
    r = requests.post(f"{BASE}/agents/digital-twin/",
                      json={"trip_id": TRIP_ID}, headers=H)
    check(r, "POST /agents/digital-twin/ (missing gps_lat/lon)", 200)  # uses defaults

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 12 — AI AGENT: Route (Shapely Geofencing)
    # ═══════════════════════════════════════════════════════════════════════
    section("12. AI AGENT — Route (Shapely Geofencing)")

    # On-route coordinates (Delhi area)
    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "gps_lat": 28.6139,
        "gps_lon": 77.2090
    }
    r = requests.post(f"{BASE}/agents/route/", json=payload, headers=H)
    check(r, "POST /agents/route/ (Delhi GPS — in corridor)", 200)

    # Far off-route coordinates (Mumbai)
    payload["gps_lat"] = 19.076
    payload["gps_lon"] = 72.877
    r = requests.post(f"{BASE}/agents/route/", json=payload, headers=H)
    check(r, "POST /agents/route/ (Mumbai GPS — off corridor)", 200)

    # Missing coords
    r = requests.post(f"{BASE}/agents/route/",
                      json={"trip_id": TRIP_ID, "truck_id": "TRK-001"}, headers=H)
    check(r, "POST /agents/route/ (missing coords → 400)", 400)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 13 — AI AGENT: Risk Fusion (Weighted/Bayesian)
    # ═══════════════════════════════════════════════════════════════════════
    section("13. AI AGENT — Risk Fusion (Weighted Bayesian Aggregator)")

    # Low signals
    payload = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "behaviour": {"anomaly_score": 0.1, "loitering_detected": False},
        "twin": {"deviation_score": 0.1, "door_state": "CLOSED", "driver_rfid_scanned": True},
        "route": {"route_risk_score": 0.05, "in_safe_corridor": True, "in_high_risk_zone": False}
    }
    r = requests.post(f"{BASE}/agents/risk-fusion/", json=payload, headers=H)
    check(r, "POST /agents/risk-fusion/ (LOW signals)", 200)

    # High signals — should trigger CRITICAL
    payload_high = {
        "trip_id": TRIP_ID,
        "truck_id": "TRK-001",
        "behaviour": {"anomaly_score": 0.9, "loitering_detected": True},
        "twin": {"deviation_score": 0.85, "door_state": "OPEN", "driver_rfid_scanned": False},
        "route": {"route_risk_score": 0.8, "in_safe_corridor": False, "in_high_risk_zone": True,
                  "deviation_km": 3.0}
    }
    r = requests.post(f"{BASE}/agents/risk-fusion/", json=payload_high, headers=H)
    check(r, "POST /agents/risk-fusion/ (HIGH signals → CRITICAL expected)", 200)

    # Empty signals
    r = requests.post(f"{BASE}/agents/risk-fusion/",
                      json={"trip_id": TRIP_ID, "truck_id": "TRK-001"}, headers=H)
    check(r, "POST /agents/risk-fusion/ (empty signals → fallback)", 200)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 14 — AI AGENT: Explainability (LLM/Template)
    # ═══════════════════════════════════════════════════════════════════════
    section("14. AI AGENT — Explainability (LLM / Rule-Based Template)")

    risk_payload = {
        "truck_id": "TRK-001",
        "risk_level": "CRITICAL",
        "composite_risk_score": 0.92,
        "confidence": 0.88,
        "component_scores": {"behaviour": 0.9, "twin": 0.85, "route": 0.8},
        "triggered_rules": ["LOITERING_DETECTED", "DOOR_OPEN_NO_RFID", "GEOFENCE_VIOLATION"],
        "fusion_method": "weighted_fallback"
    }
    decision_payload = {
        "rule_id": "R001",
        "rule_name": "CRITICAL_THEFT_ALERT",
        "actions_taken": ["sms", "email", "log_incident"],
        "risk_level": "CRITICAL"
    }
    r = requests.post(f"{BASE}/agents/explain/", json={
        "trip_id": TRIP_ID,
        "risk_payload": risk_payload,
        "decision_payload": decision_payload
    }, headers=H)
    check(r, "POST /agents/explain/ (CRITICAL alert explanation)", 200)

    # Minimal payload
    r = requests.post(f"{BASE}/agents/explain/", json={
        "trip_id": TRIP_ID,
        "risk_payload": {},
        "decision_payload": {}
    }, headers=H)
    check(r, "POST /agents/explain/ (empty payloads → template fallback)", 200)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 15 — AI AGENT: Vision Event (Legacy endpoint)
    # ═══════════════════════════════════════════════════════════════════════
    section("15. AI AGENT — Vision Event (Legacy Bridge)")

    r = requests.post(f"{BASE}/agents/vision-event/", json={
        "trip_id": TRIP_ID,
        "event_type": "Person Detected",
        "confidence": 0.95
    }, headers=H)
    check(r, "POST /agents/vision-event/ (person detected, high conf)", 201)

    r = requests.post(f"{BASE}/agents/vision-event/", json={
        "trip_id": TRIP_ID,
        "event_type": "Vehicle Intrusion",
        "confidence": 0.72
    }, headers=H)
    check(r, "POST /agents/vision-event/ (vehicle intrusion)", 201)

    r = requests.post(f"{BASE}/agents/vision-event/", json={"event_type": "Person"}, headers=H)
    check(r, "POST /agents/vision-event/ (missing trip_id → 400)", 400)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 16 — AI AGENT: Fusion Risk (GET — Legacy)
    # ═══════════════════════════════════════════════════════════════════════
    section("16. AI AGENT — Fusion Risk GET (Legacy Aggregator)")

    r = requests.get(f"{BASE}/agents/fusion-risk/?trip_id={TRIP_ID}", headers=H)
    check(r, f"GET  /agents/fusion-risk/?trip_id={TRIP_ID[:8]}…", 200)

    r = requests.get(f"{BASE}/agents/fusion-risk/", headers=H)
    check(r, "GET  /agents/fusion-risk/ (missing trip_id → 400)", 400)

    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 17 — AI AGENT: Simulation Demo
    # ═══════════════════════════════════════════════════════════════════════
    section("17. AI AGENT — Simulation / Demo Scenario")

    r = requests.post(f"{BASE}/agents/simulate/", json={"trip_id": TRIP_ID}, headers=H)
    check(r, "POST /agents/simulate/ (full demo scenario)", 200)

    r = requests.post(f"{BASE}/agents/simulate/", json={}, headers=H)
    check(r, "POST /agents/simulate/ (missing trip_id → 400)", 400)

# ═══════════════════════════════════════════════════════════════════════════
#  STEP 18 — UNAUTHENTICATED (should 401)
# ═══════════════════════════════════════════════════════════════════════════
section("18. UNAUTHENTICATED ACCESS (must all be 401)")

endpoints_401 = [
    ("GET", f"{BASE}/trucks/"),
    ("GET", f"{BASE}/trips/"),
    ("GET", f"{BASE}/alerts/"),
    ("GET", f"{BASE}/auth/me/"),
    ("GET", f"{BASE}/admin/dashboard/"),
]
for method, url in endpoints_401:
    r = requests.request(method, url)
    code = r.status_code
    label = f"{method} {url.replace(BASE, '/api')} (no token)"
    if code == 401:
        ok(label, "correctly rejected")
    else:
        fail(label, f"Expected 401, got {code}")

# ═══════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
total = passed + failed
print(f"\n{CYAN}{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  TEST SUMMARY{RESET}")
print(f"{CYAN}{BOLD}{'═'*60}{RESET}")
print(f"  {GREEN}PASSED : {passed}{RESET}")
print(f"  {RED}FAILED : {failed}{RESET}")
if warnings:
    print(f"  {YELLOW}WARNINGS: {warnings}{RESET}")
print(f"  TOTAL  : {total}")
print(f"{CYAN}{BOLD}{'═'*60}{RESET}\n")

if failed == 0:
    print(f"{GREEN}{BOLD}  🎉 All tests passed!{RESET}\n")
else:
    print(f"{RED}{BOLD}  ❌ {failed} test(s) failed — review output above.{RESET}\n")
    sys.exit(1)
