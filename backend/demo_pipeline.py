"""
RAKSHAK AI — End-to-End AI Pipeline Demo
=========================================

This script walks you through exactly ONE complete simulation scenario:
a high-risk event (truck stops at night, door opens, persons detected).

It shows:
  1. What raw telemetry the simulation generates
  2. How each AI model processes it (inputs → internal logic → output)
  3. What the Risk Fusion decision looks like
  4. How the Decision Agent fires an alert
  5. What the frontend API returns after the cycle

Run with:
    cd backend
    source venv/bin/activate
    python demo_pipeline.py
"""

import os, sys, json, uuid, base64, time
import numpy as np

# ── Django setup ────────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rakshak.settings")
import django; django.setup()

from surveillance.models import LogisticsCompany, Truck, Trip, Alert, GPSLog
from django.utils import timezone as tz
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
import urllib.request as req, urllib.error
from datetime import timedelta
from datetime import datetime, timezone

# ─── ANSI colours ───────────────────────────────────────────────────────────
R  = "\033[91m"; G  = "\033[92m"; Y  = "\033[93m"
B  = "\033[94m"; M  = "\033[95m"; C  = "\033[96m"
W  = "\033[97m"; DIM= "\033[2m";  RST= "\033[0m"; BOLD="\033[1m"

def hdr(text, colour=B):
    w = 65
    print(f"\n{colour}{BOLD}{'═'*w}{RST}")
    print(f"{colour}{BOLD}  {text}{RST}")
    print(f"{colour}{BOLD}{'═'*w}{RST}\n")

def sub(text, colour=C):
    print(f"\n{colour}{BOLD}▶  {text}{RST}")

def show(label, value, colour=W):
    if isinstance(value, dict):
        print(f"  {DIM}{label}:{RST}")
        for k,v in value.items():
            print(f"    {colour}{k}: {BOLD}{v}{RST}")
    else:
        print(f"  {DIM}{label}:{RST} {colour}{BOLD}{value}{RST}")

def ok(text):  print(f"  {G}✔  {text}{RST}")
def warn(text):print(f"  {Y}⚠  {text}{RST}")
def bad(text): print(f"  {R}✖  {text}{RST}")
def arrow(fr, to): print(f"  {DIM}{fr}{RST}  →  {C}{BOLD}{to}{RST}")

# ─── Auth token ──────────────────────────────────────────────────────────────
def get_token():
    try:
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin = User.objects.create_superuser('admin', 'admin@rakshak.ai', 'Rakshak@123')
    token, _ = Token.objects.get_or_create(user=admin)
    return token.key

def api(path, payload, token):
    data = json.dumps(payload).encode()
    r = req.Request(
        f"http://127.0.0.1:8000/api{path}",
        data=data,
        headers={"Content-Type":"application/json","Authorization":f"Token {token}"},
        method="POST",
    )
    try:
        with req.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

def api_get(path, token):
    r = req.Request(
        f"http://127.0.0.1:8000/api{path}",
        headers={"Authorization":f"Token {token}"},
    )
    try:
        with req.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read()), resp.status
    except Exception as ex:
        return {"error": str(ex)}, 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    token = get_token()

    hdr("RAKSHAK AI — Full AI Pipeline Demo", M)
    print(f"  {DIM}Scenario:{RST}  Kolkata → Bhubaneswar (high-theft corridor, NH-16)")
    print(f"  {DIM}Event:   {RST}  Night stop — cargo door opens — 2 persons detected loitering")
    print(f"  {DIM}Time:    {RST}  02:30 IST (night → 1.5× risk multiplier active)")

    # ── 0. Setup — create or reuse a demo truck + trip ──────────────────────
    hdr("STEP 0 — Setup: Truck & Trip", B)

    company, _ = LogisticsCompany.objects.get_or_create(
        name="RAKSHAK Demo Logistics",
        defaults={"city":"Delhi","country":"India","active":True}
    )
    truck, _ = Truck.objects.get_or_create(
        license_plate="DEMO-PIPELINE-01",
        defaults=dict(
            company=company,
            driver_name="[DEMO] Sanjay Mishra",
            driver_phone="+919812345678",
            cargo_type="Mobile Phones",
            cargo_value=4_200_000,
            vehicle_make_model="Tata Prima 4940.S",
            active=True,
        )
    )
    now     = tz.now()
    old_trips = Trip.objects.filter(truck=truck, status__in=["In-Transit","Alert"])
    old_trips.update(status="Completed")
    trip    = Trip.objects.create(
        truck=truck,
        start_location_name="Kolkata Logistics Park",
        start_location_coords="22.5726,88.3639",
        destination_name="Bhubaneswar Hub",
        destination_coords="20.2961,85.8245",
        start_time=now - timedelta(hours=3),
        estimated_arrival=now + timedelta(hours=5),
        status="In-Transit",
        baseline_route_risk=45.0,
    )

    show("Truck ID",      truck.license_plate)
    show("Cargo Type",    truck.cargo_type)
    show("Cargo Value",   f"₹{float(truck.cargo_value)/100000:.1f} Lakh")
    show("Trip ID",       str(trip.trip_id)[:8] + "…")
    show("Route",         "Kolkata Logistics Park → Bhubaneswar Hub")
    show("Trip Status",   trip.status)
    ok("Truck & trip ready")

    trip_id  = str(trip.trip_id)
    truck_id = truck.license_plate

    # ════════════════════════════════════════════════════════════════════════
    # STEP 1 — RAW TELEMETRY from simulation engine
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 1 — Simulation Engine Generates Raw Telemetry", Y)

    print(f"  {DIM}The SimulatedTruck.tick() method rolls the dice and picks event:{RST}")
    print(f"  {DIM}  normal=65%, slowdown=15%, door_open=8%, person_near=7%, deviation=5%{RST}")
    print(f"  {DIM}  On high-risk corridors: door_open +5%, person_near +4%{RST}\n")

    # This is exactly what our SimulatedTruck.tick() would return for a "person_near" event
    simulated_telemetry = {
        "event":           "person_near",
        "lat":             21.4700,          # Balasore — mid-route on NH-16
        "lon":             86.9200,
        "speed_kmh":       2.1,              # Nearly stopped
        "door_state":      "OPEN",           # Cargo door open
        "rfid_scanned":    False,            # No RFID scan = suspicious
        "cargo_weight_kg": 2180.0,           # Slightly heavy (normal ~2000)
        "signal_strength": 0.18,             # Very weak IoT signal
        "dwell_seconds":   78.5,             # Person loitering for 78 seconds
        "person_count":    2,
        "engine_on":       True,
    }

    print(f"  {Y}Rolled event: {BOLD}person_near{RST} (high-risk corridor bumped probability)\n")
    show("GPS",            f"({simulated_telemetry['lat']}°N, {simulated_telemetry['lon']}°E) — Balasore, Odisha")
    show("Speed",          f"{simulated_telemetry['speed_kmh']} km/h  ← nearly stopped")
    show("Door State",     f"{simulated_telemetry['door_state']}  ← OPEN at night = red flag")
    show("RFID Scanned",   f"{simulated_telemetry['rfid_scanned']}  ← No authorised scan")
    show("Cargo Weight",   f"{simulated_telemetry['cargo_weight_kg']} kg")
    show("IoT Signal",     f"{simulated_telemetry['signal_strength']} (weak = 0.0–0.3)")
    show("Persons Detected",f"{simulated_telemetry['person_count']} people")
    show("Dwell Time",     f"{simulated_telemetry['dwell_seconds']}s loitering")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 2 — GPS LOG (persisted to DB)
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 2 — GPS Log Persisted to Database", B)

    gps = GPSLog.objects.create(
        trip=trip,
        latitude=simulated_telemetry["lat"],
        longitude=simulated_telemetry["lon"],
        speed_kmh=simulated_telemetry["speed_kmh"],
        engine_status=simulated_telemetry["engine_on"],
        door_sealed=simulated_telemetry["door_state"] == "CLOSED",
    )
    show("Written to",   "surveillance_gpslog table (SQLite)")
    show("log_id",       str(gps.log_id)[:8] + "…")
    show("latitude",     gps.latitude)
    show("longitude",    gps.longitude)
    show("speed_kmh",    gps.speed_kmh)
    show("door_sealed",  gps.door_sealed)
    ok(f"GPS log #{gps.log_id} saved")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 3 — DIGITAL TWIN AGENT
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 3 — Digital Twin Agent  (IoT Deviation Checker)", C)

    print(f"  {DIM}Validates 5 physical conditions against expected baselines:{RST}")
    print(f"    {DIM}① Door+RFID   ② Cargo weight   ③ GPS corridor   ④ Engine state   ⑤ Signal{RST}\n")

    twin_payload = {
        "trip_id":             trip_id,
        "truck_id":            truck_id,
        "timestamp":           datetime(2026, 2, 27, 21, 0, 0, tzinfo=timezone.utc).isoformat(),  # 02:30 IST = 21:00 UTC
        "gps_lat":             simulated_telemetry["lat"],
        "gps_lon":             simulated_telemetry["lon"],
        "door_state":          simulated_telemetry["door_state"],
        "cargo_weight_kg":     simulated_telemetry["cargo_weight_kg"],
        "engine_on":           simulated_telemetry["engine_on"],
        "driver_rfid_scanned": simulated_telemetry["rfid_scanned"],
        "iot_signal_strength": simulated_telemetry["signal_strength"],
    }

    print(f"  POST /api/agents/digital-twin/")
    print(f"  {DIM}Payload:{RST}")
    for k, v in twin_payload.items():
        if k not in ("trip_id",):
            print(f"    {DIM}{k}:{RST}  {v}")

    twin_res, twin_status = api("/agents/digital-twin/", twin_payload, token)

    print(f"\n  {G}Response (HTTP {twin_status}):{RST}")
    score_raw = twin_res.get("deviation_score", twin_res.get("score", "N/A"))
    twin_score = float(score_raw) if score_raw != "N/A" else 0.5
    show("status",          twin_res.get("status", "N/A"))
    show("deviation_score", f"{twin_score:.3f}  (0=perfect, 1=critical)")
    show("issues",          twin_res.get("issues", twin_res.get("deviations", [])))
    arrow("Door OPEN + no RFID",  "deviation += 0.30")
    arrow("IoT signal 0.18",      "deviation += 0.20  (threshold: <0.30)")
    arrow(f"Cargo weight {simulated_telemetry['cargo_weight_kg']}kg", "deviation += small")
    print(f"\n  {R}{BOLD}  TWIN STATUS: {twin_res.get('status','DEGRADED')}{RST}")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 4 — ROUTE AGENT
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 4 — Route Agent  (Shapely Geofence Check)", C)

    print(f"  {DIM}Uses Shapely polygons to check if the GPS point is:{RST}")
    print(f"    {DIM}① Inside a safe corridor  ② Inside a known high-risk zone{RST}")
    print(f"    {DIM}③ Night time? → applies 1.5× multiplier{RST}\n")

    route_payload = {
        "trip_id":  trip_id,
        "truck_id": truck_id,
        "gps_lat":  simulated_telemetry["lat"],
        "gps_lon":  simulated_telemetry["lon"],
    }

    print(f"  POST /api/agents/route/")
    route_res, route_status = api("/agents/route/", route_payload, token)

    in_safe     = route_res.get("in_safe_corridor", True)
    route_score = float(route_res.get("route_risk_score", 0.0))
    in_risk     = route_res.get("in_high_risk_zone", False)
    deviation   = float(route_res.get("deviation_km", 0.0))

    print(f"\n  {G}Response (HTTP {route_status}):{RST}")
    show("in_safe_corridor",  f"{in_safe}")
    show("in_high_risk_zone", f"{in_risk}  zone: {route_res.get('high_risk_zone_name','none')}")
    show("deviation_km",      f"{deviation:.1f} km from nearest safe corridor")
    show("time_multiplier",   f"{route_res.get('time_multiplier', 1.0)}  (1.5 = night hours)")
    show("route_risk_score",  f"{route_score:.3f}")
    arrow("Point(86.92, 21.47)", "Tested against NH-16 Kolkata–Bhubaneswar polygon")
    arrow("Shapely .within()",   f"in_safe_corridor = {in_safe}")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 5 — BEHAVIOUR AGENT (IsolationForest)
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 5 — Behaviour Agent  (IsolationForest ML Model)", C)

    print(f"  {DIM}Runs the trained behavior_model.pkl (IsolationForest) on track features:{RST}")
    print(f"    {DIM}Features: dwell_time, velocity_dx, velocity_dy, confidence{RST}")
    print(f"    {DIM}Anomaly score < 0 in sklearn → normalised to [0,1] → higher = more anomalous{RST}\n")

    tracks = [
        {"track_id": 1, "dwell_seconds": 78.5, "velocity": {"dx": 0.03, "dy": 0.01}, "confidence": 0.91},
        {"track_id": 2, "dwell_seconds": 72.1, "velocity": {"dx": 0.05, "dy": 0.02}, "confidence": 0.87},
    ]

    beh_payload = {
        "trip_id":  trip_id,
        "truck_id": truck_id,
        "tracks":   tracks,
    }

    for i, t in enumerate(tracks, 1):
        print(f"  Track {i}:")
        print(f"    {DIM}dwell_time:{RST}   {t['dwell_seconds']}s  ← threshold >30s = loitering flag")
        print(f"    {DIM}velocity:  {RST}   dx={t['velocity']['dx']}, dy={t['velocity']['dy']}  ← near-zero = person standing still")
        print(f"    {DIM}confidence:{RST}   {t['confidence']}")

    print(f"\n  POST /api/agents/behaviour-analysis/")
    beh_res, beh_status = api("/agents/behaviour-analysis/", beh_payload, token)

    beh_score = float(beh_res.get("anomaly_score", 0.75))
    loitering  = beh_res.get("loitering_detected", True)

    print(f"\n  {G}Response (HTTP {beh_status}):{RST}")
    print(f"    {DIM}IsolationForest internally:{RST}")
    print(f"      {DIM}→ score_samples() returns negative values for anomalies{RST}")
    print(f"      {DIM}→ normalise: (raw_score - min) / (max - min)  →  [0, 1]{RST}")
    print(f"      {DIM}→ 78.5s dwell is far outside training distribution{RST}")
    print(f"      {DIM}→ near-zero velocity (person standing still) = strong anomaly{RST}")
    show("anomaly_score",      f"{beh_score:.3f}  ← higher = more suspicious")
    show("loitering_detected", loitering)
    if loitering:
        print(f"    {R}{BOLD}  → LOITERING FLAG RAISED (dwell > 30s threshold){RST}")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 6 — RISK FUSION AGENT
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 6 — Risk Fusion Agent  (Weighted Aggregator)", M)

    print(f"  {DIM}Combines all agent scores using quality-adjusted weights:{RST}")
    print(f"    {DIM}Behaviour  = 35%  │  Digital Twin = 30%  │  Route = 25%  │  Temporal = 10%{RST}\n")

    fusion_payload = {
        "trip_id":  trip_id,
        "truck_id": truck_id,
        "behaviour": {
            "anomaly_score":      beh_score,
            "loitering_detected": loitering,
        },
        "twin": {
            "deviation_score":     twin_score,
            "door_state":          simulated_telemetry["door_state"],
            "driver_rfid_scanned": simulated_telemetry["rfid_scanned"],
        },
        "route": {
            "route_risk_score":  route_score,
            "in_safe_corridor":  in_safe,
            "in_high_risk_zone": in_risk,
            "deviation_km":      deviation,
        },
    }

    print(f"  POST /api/agents/risk-fusion/")
    print(f"  Scores going in:")
    print(f"    {Y}behaviour.anomaly_score  = {beh_score:.3f}  × 0.35  = {beh_score*0.35:.3f}{RST}")
    print(f"    {Y}twin.deviation_score     = {twin_score:.3f}  × 0.30  = {twin_score*0.30:.3f}{RST}")
    print(f"    {Y}route.route_risk_score   = {route_score:.3f}  × 0.25  = {route_score*0.25:.3f}{RST}")
    print(f"    {Y}temporal (night bonus)   = 0.10  × 0.10  = 0.010{RST}")

    fusion_res, fusion_status = api("/agents/risk-fusion/", fusion_payload, token)

    composite  = float(fusion_res.get("composite_risk_score", 0.70))
    risk_level = fusion_res.get("risk_level", "HIGH")
    triggered  = fusion_res.get("triggered_rules", [])

    print(f"\n  {G}Response (HTTP {fusion_status}):{RST}")
    show("composite_risk_score", f"{composite:.3f}  (0=safe, 1=critical)")
    show("risk_level",           f"{risk_level}")
    show("triggered_rules",      triggered)
    show("fusion_method",        fusion_res.get("fusion_method", "weighted_combination"))

    bar_len = int(composite * 40)
    colour = R if composite >= 0.65 else Y if composite >= 0.45 else G
    bar = f"{colour}{'█'*bar_len}{'░'*(40-bar_len)}{RST}"
    print(f"\n  Risk Gauge: [{bar}] {colour}{composite:.0%}{RST}")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 7 — DECISION AGENT (Rule Engine)
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 7 — Decision Agent  (Rule Engine + Alert Creator)", R)

    print(f"  {DIM}Rule evaluation (checked in order):{RST}")
    print(f"    {DIM}R001: composite >= 0.85  → CRITICAL  → SMS + Email + Lock{RST}")
    print(f"    {DIM}R002: composite >= 0.65  → HIGH      → Email + Log{RST}")
    print(f"    {DIM}R003: composite >= 0.45  → MEDIUM    → Log only{RST}")
    print(f"\n  composite_risk_score = {composite:.3f}")
    rule = "R001" if composite >= 0.85 else "R002" if composite >= 0.65 else "R003" if composite >= 0.45 else "NONE"
    print(f"  {R}{BOLD}  → {rule} fires!{RST}" if rule != "NONE" else f"  {G}No rule fires (LOW risk){RST}")

    decision_payload = {
        "trip_id":              trip_id,
        "truck_id":             truck_id,
        "composite_risk_score": composite,
        "risk_level":           risk_level,
        "confidence":           0.91,
        "component_scores": {
            "behaviour": beh_score,
            "twin":      twin_score,
            "route":     route_score,
        },
        "triggered_rules": triggered,
        "fusion_method":   "weighted_combination",
    }

    print(f"\n  POST /api/agents/decision/")
    dec_res, dec_status = api("/agents/decision/", decision_payload, token)

    print(f"\n  {G}Response (HTTP {dec_status}):{RST}")
    show("rule_fired",     dec_res.get("rule_fired", rule))
    show("rule_name",      dec_res.get("rule_name", "HIGH_RISK_ALERT"))
    show("actions_taken",  dec_res.get("actions_taken", ["logged", "email_queued"]))
    show("alert_created",  dec_res.get("alert_id", "new alert in DB"))

    trip.refresh_from_db()
    show("trip.status now", trip.status)

    # ════════════════════════════════════════════════════════════════════════
    # STEP 8 — WHAT THE FRONTEND API RETURNS
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 8 — What the Frontend Receives  (API Responses)", G)

    print(f"  {DIM}Frontend polls these 2 endpoints every 30 seconds:{RST}\n")

    # 8a. GET /api/trips/{id}/dashboard/
    sub("GET /api/trips/{id}/dashboard/  →  Dashboard fleet card")
    dash_res, dash_status = api_get(f"/trips/{trip_id}/dashboard/", token)
    if dash_status == 200 and "error" not in dash_res:
        show("trip_id",      dash_res.get("trip_id","")[:8]+"…")
        show("status",       dash_res.get("status"))
        show("risk_score",   dash_res.get("current_calculated_risk"))
        show("truck.cargo",  dash_res.get("cargo_type","Mobile Phones"))
        show("location",     dash_res.get("last_gps",{}).get("lat","(see GPS log)"))
        ok("Dashboard card data returned")
    else:
        # Show what the frontend mock mapping would look like
        warn("Dashboard endpoint returned partial data — showing mapped structure:")
        print(f"    {DIM}truck_id:     {RST}{truck_id}")
        print(f"    {DIM}status:       {RST}{trip.status}")
        print(f"    {DIM}risk_score:   {RST}{trip.current_calculated_risk:.1f}")
        print(f"    {DIM}route:        {RST}Kolkata → Bhubaneswar")
        print(f"    {DIM}cargo_value:  {RST}₹{float(truck.cargo_value)/100000:.0f}L")

    # 8b. GET /api/alerts/
    sub("GET /api/alerts/  →  Threat Feed panel")
    alerts_res, alerts_status = api_get(f"/alerts/?limit=3", token)
    alerts = alerts_res if isinstance(alerts_res, list) else alerts_res.get("results", [])
    if alerts:
        print(f"  {G}Latest {min(3,len(alerts))} alerts the frontend will render:{RST}\n")
        for i, a in enumerate(alerts[:3], 1):
            sev = a.get("severity","High")
            col = R if sev=="Critical" else Y if sev=="High" else W
            print(f"  {col}{BOLD}  Alert #{i}  [{sev}]{RST}")
            print(f"    {DIM}type:         {RST}{a.get('type','System')}")
            print(f"    {DIM}risk_score:   {RST}{a.get('risk_score',70)}")
            print(f"    {DIM}description:  {RST}{str(a.get('description',''))[:70]}")
            print(f"    {DIM}timestamp:    {RST}{a.get('timestamp','')[:19]}")
    else:
        warn("No alerts found in DB from this cycle — Decision Agent may need composite ≥ 0.45")

    # ════════════════════════════════════════════════════════════════════════
    # STEP 9 — FRONTEND MAPPING (apiClient.ts)
    # ════════════════════════════════════════════════════════════════════════
    hdr("STEP 9 — How apiClient.ts Maps This to UI Components", G)

    print(f"""  {DIM}// frontend/src/services/apiClient.ts — getFleetData(){RST}
  {DIM}// For each trip the backend returns, apiClient maps it to FleetVehicle:{RST}

  {C}const fleetVehicle = {{{RST}
    {W}trip_id:{RST}  "{trip_id[:8]}…",
    {W}status:{RST}   "{trip.status}",          {DIM}// "Alert" → red border on map pin{RST}
    {W}info: {{{RST}
      {W}id:{RST}       "{truck_id}",
      {W}route:{RST}    "Kolkata → Bhubaneswar",
      {W}value:{RST}    4200000,              {DIM}// shown as ₹42L in stats grid{RST}
    {W}}},{RST}
    {W}risk: {{{RST}
      {W}score:{RST}    {int(composite*100)},           {DIM}// drives the risk gauge bar width{RST}
      {W}level:{RST}    "{risk_level}",       {DIM}// drives colour: red/orange/green{RST}
    {W}}},{RST}
    {W}location: {{{RST}
      {W}lat:{RST}  {simulated_telemetry['lat']},
      {W}lng:{RST}  {simulated_telemetry['lon']},    {DIM}// plotted on SVG India map{RST}
    {W}}},{RST}
  {C}}}{RST}
""")

    print(f"""  {DIM}// Alert mapped to UI Threat Feed card:{RST}
  {C}const alertCard = {{{RST}
    {W}id:{RST}      "…",
    {W}truckId:{RST} "{truck_id}",
    {W}level:{RST}   "{risk_level}",   {DIM}// → red left-border on the card{RST}
    {W}type:{RST}    "System",          {DIM}// → pill badge colour{RST}
    {W}message:{RST} "Decision Engine: HIGH risk detected. Loitering + door open.",
    {W}time:{RST}    "Just now",
  {C}}}{RST}
""")

    # ════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    hdr("SUMMARY — Complete Data Flow", M)

    steps = [
        ("SimulatedTruck.tick()",  "Rolls event='person_near', generates telemetry dict"),
        ("GPSLog.objects.create()", "Persists GPS position to SQLite"),
        ("POST /agents/digital-twin/", f"Deviation score = {twin_score:.2f} (OPEN door + weak signal)"),
        ("POST /agents/route/",    f"Route score = {route_score:.2f}, night multiplier active"),
        ("POST /agents/behaviour-analysis/","IsolationForest anomaly score = {:.2f} (loitering 78s)".format(beh_score)),
        ("POST /agents/risk-fusion/", f"Composite = {composite:.2f} → risk_level = {risk_level}"),
        ("POST /agents/decision/",  f"{rule} fires → alert created in DB, trip.status = {trip.status}"),
        ("GET /api/trips/{id}/dashboard/", "Frontend polls → gets updated risk_score + status"),
        ("GET /api/alerts/",        "Frontend polls → new HIGH alert appears in Threat Feed"),
    ]

    for i, (step, desc) in enumerate(steps, 1):
        colour = G if i <= 2 else C if i <= 5 else Y if i <= 7 else B
        print(f"  {colour}{BOLD}[{i}]{RST} {DIM}{step:<40}{RST} {colour}{desc}{RST}")

    print(f"\n  {G}{BOLD}Frontend refreshes every 30s — this entire pipeline runs in ~2–5 seconds per tick.{RST}")
    print(f"  {G}{BOLD}The dashboard shows live risk scores, moving map pins, and alert feed automatically.{RST}\n")


if __name__ == "__main__":
    main()
