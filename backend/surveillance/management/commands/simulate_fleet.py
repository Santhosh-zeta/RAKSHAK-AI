"""
RAKSHAK AI — Realtime Fleet Simulation Engine
==============================================

Django management command that continuously generates realistic truck telemetry,
feeds it through every AI agent, and persists the results to the database
so the frontend sees live, evolving alerts and risk scores.

Usage:
    python manage.py simulate_fleet
    python manage.py simulate_fleet --trucks 5 --interval 15
    python manage.py simulate_fleet --once          # Single cycle then exit (for testing)
    python manage.py simulate_fleet --reset         # Wipe old sim data and start fresh
"""

import time
import random
import math
import json
import base64
import logging
import os
import sys
import uuid
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional

import django
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

logger = logging.getLogger("rakshak.simulation")

# ─── Indian Logistics Corridors ─────────────────────────────────────────────
# Each corridor is a list of (lat, lon, location_name) waypoints

CORRIDORS = [
    {
        "name":        "Delhi → Jaipur (NH-48)",
        "cargo":       "Electronics",
        "value":       1_500_000,
        "risk_base":   0.25,
        "waypoints": [
            (28.6139, 77.2090, "Delhi Depot"),
            (28.4089, 76.9944, "Gurgaon Checkpoint"),
            (28.0800, 76.7700, "Rewari"),
            (27.9104, 76.5834, "Narnaul"),
            (27.5400, 76.2000, "Sikar Road"),
            (26.9124, 75.7873, "Jaipur Warehouse"),
        ],
    },
    {
        "name":        "Mumbai → Pune (NH-48)",
        "cargo":       "Pharmaceuticals",
        "value":       3_200_000,
        "risk_base":   0.20,
        "waypoints": [
            (19.0760, 72.8777, "Mumbai Freight Terminal"),
            (18.9973, 73.1169, "Khopoli"),
            (18.8735, 73.3200, "Khalapur"),
            (18.6500, 73.7000, "Lonavala"),
            (18.5204, 73.8567, "Pune Distribution Centre"),
        ],
    },
    {
        "name":        "Bangalore → Chennai (NH-44)",
        "cargo":       "Mobile Phones",
        "value":       4_200_000,
        "risk_base":   0.30,
        "waypoints": [
            (12.9716, 77.5946, "Bangalore Export Hub"),
            (12.7000, 77.9000, "Hosur"),
            (12.4500, 78.2500, "Krishnagiri"),
            (12.2000, 78.5500, "Vellore"),
            (13.0827, 80.2707, "Chennai Port"),
        ],
    },
    {
        "name":        "Kolkata → Bhubaneswar (NH-16)",
        "cargo":       "Steel Coils",
        "value":       420_000,
        "risk_base":   0.45,   # High-theft corridor
        "waypoints": [
            (22.5726, 88.3639, "Kolkata Logistics Park"),
            (22.2000, 88.1500, "Uluberia"),
            (21.9000, 87.7000, "Mecheda"),
            (21.4700, 86.9200, "Balasore"),
            (20.2961, 85.8245, "Bhubaneswar Hub"),
        ],
    },
    {
        "name":        "Hyderabad → Nagpur (NH-44)",
        "cargo":       "FMCG Goods",
        "value":       680_000,
        "risk_base":   0.35,
        "waypoints": [
            (17.3850, 78.4867, "Hyderabad Warehouse"),
            (17.8000, 78.8000, "Bhongir"),
            (18.4386, 79.1288, "Karimnagar"),
            (18.9000, 79.5500, "Mancherial"),
            (21.1458, 79.0882, "Nagpur Depot"),
        ],
    },
]

DRIVER_NAMES = [
    "Ravi Kumar", "Suresh Patel", "Mohan Singh", "Arjun Sharma",
    "Rajesh Verma", "Dinesh Yadav", "Vijay Nair", "Sanjay Mishra",
    "Pradeep Gupta", "Ramesh Joshi",
]

LICENSE_PREFIXES = ["DL", "MH", "KA", "WB", "TS", "AP"]

# ─── Synthetic Frame Generator ───────────────────────────────────────────────

def _make_synthetic_frame_b64(width: int = 160, height: int = 120) -> str:
    """
    Generate a tiny synthetic JPEG-like image as base64.
    Uses numpy to create a realistic-looking dark scene
    (simulates a truck cargo bay camera at night).
    """
    arr = np.random.randint(20, 80, (height, width, 3), dtype=np.uint8)
    # Add a slightly brighter region to simulate cargo area lighting
    arr[height//3:2*height//3, width//4:3*width//4] += 30
    arr = arr.clip(0, 255).astype(np.uint8)
    try:
        import cv2
        _, buf = cv2.imencode('.jpg', arr, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return base64.b64encode(buf.tobytes()).decode()
    except ImportError:
        # Fallback: raw RGB bytes encoded directly
        raw = arr.tobytes()
        return base64.b64encode(raw).decode()


# ─── SimulatedTruck ──────────────────────────────────────────────────────────

class SimulatedTruck:
    """
    Tracks the live state of one simulated truck as it progresses through
    its corridor. Each tick() call advances the truck and decides what
    kind of event to inject (normal, suspicious, anomalous, critical).
    """

    EVENT_WEIGHTS = {
        "normal":      65,   # Routine transit
        "slowdown":    15,   # Speed drop — could be traffic or suspicious stop
        "door_open":   8,    # Door opened without RFID — major red flag
        "person_near": 7,    # Person detected near cargo hatch
        "deviation":   5,    # Slight GPS deviation off corridor
    }

    def __init__(self, truck_db, trip_db, corridor: dict):
        self.truck_db       = truck_db
        self.trip_db        = trip_db
        self.corridor       = corridor
        self.waypoints      = corridor["waypoints"]
        self.waypoint_idx   = 0
        self.progress       = 0.0      # 0→1 between current waypoint pair
        self.speed_kmh      = random.uniform(55, 75)
        self.door_state     = "CLOSED"
        self.rfid_scanned   = True
        self.cargo_weight   = random.uniform(1800, 2200)
        self.signal_str     = random.uniform(0.7, 1.0)
        self.event_streak   = 0        # Consecutive event ticks
        self.current_event  = "normal"
        self.completed      = False
        self.dwell_seconds  = 0.0      # Simulated camera dwell time
        self.person_count   = 0
        self.tick_count     = 0

    @property
    def current_lat(self) -> float:
        if self.waypoint_idx >= len(self.waypoints) - 1:
            return self.waypoints[-1][0]
        a = self.waypoints[self.waypoint_idx]
        b = self.waypoints[self.waypoint_idx + 1]
        return a[0] + (b[0] - a[0]) * self.progress

    @property
    def current_lon(self) -> float:
        if self.waypoint_idx >= len(self.waypoints) - 1:
            return self.waypoints[-1][1]
        a = self.waypoints[self.waypoint_idx]
        b = self.waypoints[self.waypoint_idx + 1]
        return a[1] + (b[1] - a[1]) * self.progress

    def tick(self, interval_s: int) -> dict:
        """Advance the truck by one simulation interval. Returns telemetry dict."""
        self.tick_count += 1

        # ── Advance route progress ──────────────────────────────────────────
        if self.waypoint_idx < len(self.waypoints) - 1:
            step   = (self.speed_kmh * 1000 / 3600) * interval_s
            a      = self.waypoints[self.waypoint_idx]
            b      = self.waypoints[self.waypoint_idx + 1]
            seg_m  = _haversine(a[0], a[1], b[0], b[1]) * 1000
            self.progress += step / max(seg_m, 1)

            if self.progress >= 1.0:
                self.progress = 0.0
                self.waypoint_idx += 1

            if self.waypoint_idx >= len(self.waypoints) - 1:
                self.completed = True

        # ── Pick event for this tick ────────────────────────────────────────
        if self.event_streak > 0:
            # Continue the current event for a few ticks
            self.event_streak -= 1
        else:
            # Choose new event
            choices   = list(self.EVENT_WEIGHTS.keys())
            weights   = list(self.EVENT_WEIGHTS.values())
            # Increase risky events if on a high-risk corridor
            if self.corridor.get("risk_base", 0) > 0.35:
                weights[choices.index("door_open")]   += 5
                weights[choices.index("person_near")] += 4
            self.current_event = random.choices(choices, weights=weights)[0]
            self.event_streak  = random.randint(1, 3)

        # ── Apply event ─────────────────────────────────────────────────────
        if self.current_event == "normal":
            self.speed_kmh    = random.uniform(55, 75)
            self.door_state   = "CLOSED"
            self.rfid_scanned = True
            self.signal_str   = random.uniform(0.7, 1.0)
            self.dwell_seconds = 0.0
            self.person_count  = 0

        elif self.current_event == "slowdown":
            self.speed_kmh    = random.uniform(5, 20)   # Unusual slow / stop
            self.door_state   = "CLOSED"
            self.rfid_scanned = True
            self.dwell_seconds = random.uniform(0, 15)
            self.person_count  = 0

        elif self.current_event == "door_open":
            self.speed_kmh    = random.uniform(0, 5)    # Basically stopped
            self.door_state   = "OPEN"
            self.rfid_scanned = False                    # No RFID scan = big flag
            self.signal_str   = random.uniform(0.1, 0.4)
            self.dwell_seconds = random.uniform(20, 90)
            self.person_count  = random.randint(1, 2)

        elif self.current_event == "person_near":
            self.speed_kmh    = random.uniform(0, 10)
            self.door_state   = random.choice(["OPEN", "CLOSED"])
            self.rfid_scanned = False
            self.dwell_seconds = random.uniform(30, 120)
            self.person_count  = random.randint(1, 3)

        elif self.current_event == "deviation":
            # Add noise GPS offset
            self.speed_kmh    = random.uniform(30, 50)
            self.door_state   = "CLOSED"
            self.rfid_scanned = True
            self.dwell_seconds = 0.0
            self.person_count  = 0

        # Cargo weight anomaly (random small drift)
        self.cargo_weight += random.uniform(-15, 15)
        self.cargo_weight  = max(500, min(3000, self.cargo_weight))

        return {
            "event":             self.current_event,
            "lat":               self.current_lat,
            "lon":               self.current_lon,
            "speed_kmh":         round(self.speed_kmh, 1),
            "door_state":        self.door_state,
            "rfid_scanned":      self.rfid_scanned,
            "cargo_weight_kg":   round(self.cargo_weight, 1),
            "signal_strength":   round(max(0.05, min(1.0, self.signal_str)), 2),
            "dwell_seconds":     round(self.dwell_seconds, 1),
            "person_count":      self.person_count,
            "engine_on":         self.speed_kmh > 2,
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in km between two GPS points."""
    R   = 6371
    φ1  = math.radians(lat1); φ2 = math.radians(lat2)
    Δφ  = math.radians(lat2 - lat1)
    Δλ  = math.radians(lon2 - lon1)
    a   = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _make_token() -> str:
    """Get or create the admin user's DRF token for API calls."""
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token
    try:
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin = User.objects.create_superuser('admin', 'admin@rakshak.ai', 'Rakshak@123')
        logger.info("[SIM] Created admin user")
    token, _ = Token.objects.get_or_create(user=admin)
    return token.key


def _api(method: str, path: str, payload: dict, token: str) -> Optional[dict]:
    """Make an HTTP call to the local backend API."""
    import urllib.request as req
    import urllib.error
    base = "http://127.0.0.1:8000/api"
    data = json.dumps(payload).encode()
    request = req.Request(
        f"{base}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        },
        method=method.upper(),
    )
    try:
        with req.urlopen(request, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        logger.warning(f"[SIM] HTTP {e.code} {path}: {body}")
        return None
    except Exception as e:
        logger.warning(f"[SIM] {path} failed: {e}")
        return None


# ─── Management Command ──────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Run the RAKSHAK AI realtime fleet simulation engine"

    def add_arguments(self, parser):
        parser.add_argument("--trucks",   type=int, default=5,
                            help="Number of trucks to simulate (default: 5)")
        parser.add_argument("--interval", type=int, default=20,
                            help="Seconds between simulation ticks (default: 20)")
        parser.add_argument("--once",     action="store_true",
                            help="Run one cycle then exit (useful for testing)")
        parser.add_argument("--reset",    action="store_true",
                            help="Delete all previous sim data before starting")

    def handle(self, *args, **options):
        from surveillance.models import LogisticsCompany, Truck, Trip, Alert, GPSLog

        n_trucks  = options["trucks"]
        interval  = options["interval"]
        run_once  = options["once"]
        do_reset  = options["reset"]

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*62}\n"
            f"  RAKSHAK AI — Fleet Simulation Engine\n"
            f"  Trucks: {n_trucks}   Interval: {interval}s\n"
            f"{'='*62}\n"
        ))

        # ── 1. Get admin token (needed for API calls) ────────────────────────
        token = _make_token()
        self.stdout.write(self.style.HTTP_INFO(f"  Auth token: {token[:12]}..."))

        # ── 2. Optional reset ────────────────────────────────────────────────
        if do_reset:
            Alert.objects.filter(trip__truck__driver_name__startswith="[SIM]").delete()
            Trip.objects.filter(truck__driver_name__startswith="[SIM]").delete()
            Truck.objects.filter(driver_name__startswith="[SIM]").delete()
            self.stdout.write(self.style.WARNING("  Old simulation data cleared."))

        # ── 3. Get or create a demo company ─────────────────────────────────
        company, _ = LogisticsCompany.objects.get_or_create(
            name="RAKSHAK Demo Logistics",
            defaults={"city": "Delhi", "country": "India", "active": True}
        )

        # ── 4. Create trucks + active trips ──────────────────────────────────
        sim_trucks = []
        for i in range(n_trucks):
            corridor = CORRIDORS[i % len(CORRIDORS)]
            plate    = f"SIM-{i+1:02d}-RAKSHAK"
            driver   = f"[SIM] {DRIVER_NAMES[i % len(DRIVER_NAMES)]}"

            # Reuse existing sim truck if possible
            truck_qs = Truck.objects.filter(license_plate=plate)
            if truck_qs.exists():
                truck_db = truck_qs.first()
            else:
                truck_db = Truck.objects.create(
                    company=company,
                    driver_name=driver,
                    driver_phone=f"+9198{random.randint(10000000,99999999)}",
                    license_plate=plate,
                    cargo_type=corridor["cargo"],
                    cargo_value=corridor["value"],
                    vehicle_make_model="Tata Prima 4940.S",
                    active=True,
                )

            # Create new In-Transit trip
            start_wp = corridor["waypoints"][0]
            end_wp   = corridor["waypoints"][-1]
            now      = dj_timezone.now()
            trip_db  = Trip.objects.create(
                truck=truck_db,
                start_location_name=start_wp[2],
                start_location_coords=f"{start_wp[0]},{start_wp[1]}",
                destination_name=end_wp[2],
                destination_coords=f"{end_wp[0]},{end_wp[1]}",
                start_time=now,
                estimated_arrival=now + timedelta(hours=8),
                status="In-Transit",
                baseline_route_risk=corridor["risk_base"] * 100,
            )

            sim_trucks.append(SimulatedTruck(truck_db, trip_db, corridor))
            self.stdout.write(f"  ✅  Truck {plate} | {corridor['name']}")

        self.stdout.write(self.style.SUCCESS(f"\n  Simulation running. Press Ctrl+C to stop.\n"))

        # ── 5. Main simulation loop ───────────────────────────────────────────
        cycle = 0
        while True:
            cycle += 1
            self.stdout.write(self.style.HTTP_INFO(
                f"\n{'─'*60}\n  TICK #{cycle:04d}  {datetime.now().strftime('%H:%M:%S')}\n{'─'*60}"
            ))

            for st in sim_trucks:
                if st.completed:
                    # Reset to start a new trip on the same corridor
                    st.waypoint_idx = 0
                    st.progress     = 0.0
                    st.completed    = False
                    old_trip        = st.trip_db
                    old_trip.status = "Completed"
                    old_trip.save()

                    now = dj_timezone.now()
                    st.trip_db = Trip.objects.create(
                        truck=st.truck_db,
                        start_location_name=st.waypoints[0][2],
                        start_location_coords=f"{st.waypoints[0][0]},{st.waypoints[0][1]}",
                        destination_name=st.waypoints[-1][2],
                        destination_coords=f"{st.waypoints[-1][0]},{st.waypoints[-1][1]}",
                        start_time=now,
                        estimated_arrival=now + timedelta(hours=8),
                        status="In-Transit",
                        baseline_route_risk=st.corridor["risk_base"] * 100,
                    )
                    self.stdout.write(f"  ↩  {st.truck_db.license_plate} — trip reset")
                    continue

                tel = st.tick(interval)
                trip_id  = str(st.trip_db.trip_id)
                truck_id = st.truck_db.license_plate
                event    = tel["event"]

                label = {
                    "normal":      "🟢",
                    "slowdown":    "🟡",
                    "door_open":   "🔴",
                    "person_near": "🔴",
                    "deviation":   "🟠",
                }.get(event, "⚪")
                self.stdout.write(
                    f"  {label} {truck_id[:18]:<18} | "
                    f"event={event:<12} | GPS({tel['lat']:.4f},{tel['lon']:.4f}) | "
                    f"speed={tel['speed_kmh']}kmh"
                )

                # ── A. Log GPS ───────────────────────────────────────────────
                try:
                    GPSLog.objects.create(
                        trip=st.trip_db,
                        latitude=tel["lat"],
                        longitude=tel["lon"],
                        speed_kmh=tel["speed_kmh"],
                        engine_status=tel["engine_on"],
                        door_sealed=tel["door_state"] == "CLOSED",
                    )
                except Exception as gps_err:
                    self.stdout.write(self.style.WARNING(f"    ⚠ GPS log failed: {gps_err}"))

                # ── B. Digital Twin ──────────────────────────────────────────
                twin_res = _api("POST", "/agents/digital-twin/", {
                    "trip_id":             trip_id,
                    "truck_id":            truck_id,
                    "timestamp":           datetime.now(timezone.utc).isoformat(),
                    "gps_lat":             tel["lat"],
                    "gps_lon":             tel["lon"],
                    "door_state":          tel["door_state"],
                    "cargo_weight_kg":     tel["cargo_weight_kg"],
                    "engine_on":           tel["engine_on"],
                    "driver_rfid_scanned": tel["rfid_scanned"],
                    "iot_signal_strength": tel["signal_strength"],
                }, token)
                twin_score = twin_res.get("deviation_score", 0.0) if twin_res else 0.0

                # ── C. Route Agent ───────────────────────────────────────────
                route_res = _api("POST", "/agents/route/", {
                    "trip_id":  trip_id,
                    "truck_id": truck_id,
                    "gps_lat":  tel["lat"],
                    "gps_lon":  tel["lon"],
                }, token)
                route_score = route_res.get("route_risk_score", 0.0) if route_res else 0.0

                # ── D. Behaviour Agent ───────────────────────────────────────
                # Only call if persons detected or dwell time is notable
                behaviour_score = 0.0
                if tel["person_count"] > 0 or tel["dwell_seconds"] > 10:
                    tracks = [
                        {
                            "track_id":      j + 1,
                            "dwell_seconds": tel["dwell_seconds"] + random.uniform(-5, 5),
                            "velocity":      {"dx": random.uniform(-1, 1), "dy": random.uniform(-1, 1)},
                            "confidence":    random.uniform(0.70, 0.95),
                        }
                        for j in range(max(1, tel["person_count"]))
                    ]
                    beh_res = _api("POST", "/agents/behaviour-analysis/", {
                        "trip_id":  trip_id,
                        "truck_id": truck_id,
                        "tracks":   tracks,
                    }, token)
                    behaviour_score = beh_res.get("anomaly_score", 0.0) if beh_res else 0.0

                # ── E. Perception Agent (only on person/door_open events) ────
                if event in ("person_near", "door_open"):
                    frame_b64 = _make_synthetic_frame_b64(160, 120)
                    perc_res  = _api("POST", "/agents/perception/", {
                        "trip_id":  trip_id,
                        "truck_id": truck_id,
                        "frame_id": st.tick_count,
                        "frame_b64": frame_b64,
                    }, token)
                    if perc_res:
                        self.stdout.write(
                            f"    👁  Perception → {perc_res.get('track_count', 0)} tracks, "
                            f"{perc_res.get('person_count', 0)} persons"
                        )

                # ── F. Risk Fusion ───────────────────────────────────────────
                fusion_payload = {
                    "trip_id":  trip_id,
                    "truck_id": truck_id,
                    "behaviour": {
                        "anomaly_score":      behaviour_score,
                        "loitering_detected": tel["dwell_seconds"] > 30,
                    },
                    "twin": {
                        "deviation_score":     twin_score,
                        "door_state":          tel["door_state"],
                        "driver_rfid_scanned": tel["rfid_scanned"],
                    },
                    "route": {
                        "route_risk_score":  route_score,
                        "in_safe_corridor":  route_res.get("in_safe_corridor", True) if route_res else True,
                        "in_high_risk_zone": route_res.get("in_high_risk_zone", False) if route_res else False,
                        "deviation_km":      route_res.get("deviation_km", 0.0) if route_res else 0.0,
                    },
                }
                fusion_res = _api("POST", "/agents/risk-fusion/", fusion_payload, token)
                composite  = fusion_res.get("composite_risk_score", 0.0) if fusion_res else 0.0
                risk_level = fusion_res.get("risk_level", "LOW") if fusion_res else "LOW"

                self.stdout.write(
                    f"    📊 Fusion → composite={composite:.2f} level={risk_level}"
                )

                # ── G. Decision Agent (only if risk is notable) ──────────────
                if composite >= 0.45:
                    triggered = fusion_res.get("triggered_rules", []) if fusion_res else []
                    dec_res   = _api("POST", "/agents/decision/", {
                        "trip_id":              trip_id,
                        "truck_id":             truck_id,
                        "composite_risk_score": composite,
                        "risk_level":           risk_level,
                        "confidence":           round(random.uniform(0.80, 0.96), 2),
                        "component_scores": {
                            "behaviour": behaviour_score,
                            "twin":      twin_score,
                            "route":     route_score,
                        },
                        "triggered_rules": triggered,
                        "fusion_method":   "weighted_fallback",
                    }, token)

                    if dec_res and dec_res.get("rule_fired"):
                        rule = dec_res["rule_fired"]
                        self.stdout.write(
                            self.style.ERROR(
                                f"    🚨 Decision → Rule {rule} fired! "
                                f"Actions: {dec_res.get('actions_taken', [])}"
                            )
                        )

                        # ── H. Explainability Agent ──────────────────────────
                        _api("POST", "/agents/explain/", {
                            "trip_id":    trip_id,
                            "incident_id": str(uuid.uuid4()),
                            "risk_payload": {
                                "truck_id":            truck_id,
                                "risk_level":          risk_level,
                                "composite_risk_score": composite,
                                "confidence":          0.90,
                                "component_scores": {
                                    "behaviour": behaviour_score,
                                    "twin":      twin_score,
                                    "route":     route_score,
                                },
                                "triggered_rules": triggered,
                                "fusion_method":   "weighted_fallback",
                            },
                            "decision_payload": {
                                "rule_name":    dec_res.get("rule_name", ""),
                                "actions_taken": dec_res.get("actions_taken", []),
                            },
                        }, token)

            if run_once:
                self.stdout.write(self.style.SUCCESS("\n  ✅ Single cycle complete."))
                break

            self.stdout.write(f"\n  ⏱  Sleeping {interval}s…")
            time.sleep(interval)
