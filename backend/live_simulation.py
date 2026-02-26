import os
import sys
import json
import uuid
import time
import math
import random
from datetime import datetime, timezone, timedelta
import urllib.request as req, urllib.error

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rakshak.settings")
import django; django.setup()

from surveillance.models import LogisticsCompany, Truck, Trip, GPSLog
from surveillance.services.map_service import GeoSpatialService
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

# ANSI colours for terminal
G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; C = "\033[96m"; W = "\033[97m"; DIM = "\033[2m"; RST = "\033[0m"

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
        headers={"Content-Type": "application/json", "Authorization": f"Token {token}"},
        method="POST",
    )
    try:
        with req.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

def calculate_heading(p1, p2):
    lon1, lat1 = map(math.radians, p1)
    lon2, lat2 = map(math.radians, p2)
    dLon = lon2 - lon1
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360) % 360

def run_live_simulation():
    print(f"{C}========================================={RST}")
    print(f"{C}STARTING LIVE AI SIMULATION PIPELINE{RST}")
    print(f"{C}========================================={RST}\n")
    
    token = get_token()
    
    # 1. Setup Data
    company, _ = LogisticsCompany.objects.get_or_create(
        name="RAKSHAK Live Sim Logistics",
        defaults={"city": "Chennai", "country": "India", "active": True}
    )
    truck, _ = Truck.objects.get_or_create(
        license_plate="LIVE-SIM-02",
        defaults=dict(
            company=company,
            driver_name="Rajesh Kumar",
            driver_phone="+919876543210",
            cargo_type="Electronics",
            cargo_value=5_000_000,
            vehicle_make_model="Ashok Leyland",
            active=True,
        )
    )
    
    # Clean old trips for this truck
    Trip.objects.filter(truck=truck).update(status="Completed")
    
    start_loc = "80.2707,13.0827" # Chennai
    dest_loc = "77.5946,12.9716"  # Bangalore
    
    now = django.utils.timezone.now()
    trip = Trip.objects.create(
        truck=truck,
        start_location_name="Chennai Hub",
        start_location_coords=start_loc,
        destination_name="Bangalore Warehouse",
        destination_coords=dest_loc,
        start_time=now - timedelta(minutes=10),
        estimated_arrival=now + timedelta(hours=6),
        status="In-Transit",
        baseline_route_risk=30.0,
    )
    
    trip_id = str(trip.trip_id)
    truck_id = truck.license_plate
    
    print(f"[{G}SETUP{RST}] Trip initialized: {trip_id} for Truck: {truck_id}")
    
    # 2. Get Route from OSRM
    print(f"[{G}OSRM{RST}] Fetching real coordinates for route...")
    route_info = GeoSpatialService.calculate_route(start_loc, dest_loc)
    if not route_info.get("success"):
        print(f"[{R}ERROR{RST}] Failed to get route: {route_info.get('error')}")
        return
        
    coords = route_info["geometry"]["coordinates"]
    
    # Downsample points for speed, to max 100 points
    step = max(1, len(coords) // 100)
    sim_coords = coords[::step]
    total_steps = len(sim_coords)
    print(f"[{G}OSRM{RST}] Route loaded. Simulation length: {total_steps} points.\n")
    
    # 3. Step through the route and run AI agents
    for i in range(total_steps):
        curr_pt = sim_coords[i]
        lon, lat = curr_pt[0], curr_pt[1]
        
        # Heading calculation
        heading = 0.0
        if i < total_steps - 1:
             heading = calculate_heading(curr_pt, sim_coords[i+1])
             
        # Generate simulation events
        # Baseline normal behavior
        speed = round(random.uniform(50.0, 75.0), 1)
        door_state = "CLOSED"
        rfid = True
        signal = random.uniform(0.7, 1.0)
        weight = 2000.0
        dwell = 0.0
        engine = True
        
        # Randomly trigger anomalies 5% of the time
        event_label = "normal"
        if random.random() < 0.05:
            event_type = random.choice(["door", "speed", "loitering"])
            if event_type == "door":
                door_state = "OPEN"
                rfid = False
                event_label = "Door Anomalous"
            elif event_type == "speed":
                speed = 2.0
                event_label = "Extremely Low Speed"
            elif event_type == "loitering":
                speed = 0.5
                dwell = random.uniform(40.0, 90.0) # loitering
                event_label = "Loitering Detected"
                
        print(f"{C}--- Step {i+1}/{total_steps} | Event: {event_label} ---{RST}")
        print(f"  {DIM}GPS:{RST} {lat:.4f}, {lon:.4f}  {DIM}Speed:{RST} {speed} km/h")
        
        # A) Save GPS Log via ORM
        gps = GPSLog.objects.create(
            trip=trip,
            latitude=lat,
            longitude=lon,
            speed_kmh=speed,
            engine_status=engine,
            door_sealed=(door_state=="CLOSED")
        )
        
        # B) Digital Twin Agent
        twin_payload = {
            "trip_id": trip_id,
            "truck_id": truck_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gps_lat": lat,
            "gps_lon": lon,
            "door_state": door_state,
            "cargo_weight_kg": weight,
            "engine_on": engine,
            "driver_rfid_scanned": rfid,
            "iot_signal_strength": signal,
        }
        twin_res, _ = api("/agents/digital-twin/", twin_payload, token)
        twin_score = float(twin_res.get("deviation_score", 0.0))
        
        # C) Route Agent
        route_payload = {
            "trip_id": trip_id,
            "truck_id": truck_id,
            "gps_lat": lat,
            "gps_lon": lon,
        }
        route_res, _ = api("/agents/route/", route_payload, token)
        route_score = float(route_res.get("route_risk_score", 0.0))
        in_safe = route_res.get("in_safe_corridor", True)
        in_risk = route_res.get("in_high_risk_zone", False)
        deviation = float(route_res.get("deviation_km", 0.0))
        
        # D) Behaviour Agent
        # Fake track using current speed/dwell to test ML model
        tracks = [{
            "track_id": 1,
            "dwell_seconds": dwell,
            "velocity": {"dx": max(0.01, speed/1000), "dy": max(0.01, speed/1000)},
            "confidence": 0.95
        }]
        beh_payload = {
            "trip_id": trip_id,
            "truck_id": truck_id,
            "tracks": tracks,
        }
        beh_res, _ = api("/agents/behaviour-analysis/", beh_payload, token)
        beh_score = float(beh_res.get("anomaly_score", 0.0))
        loitering = beh_res.get("loitering_detected", False)
        
        # E) Risk Fusion Agent
        fusion_payload = {
            "trip_id": trip_id,
            "truck_id": truck_id,
            "behaviour": {
                "anomaly_score": beh_score,
                "loitering_detected": loitering,
            },
            "twin": {
                "deviation_score": twin_score,
                "door_state": door_state,
                "driver_rfid_scanned": rfid,
            },
            "route": {
                "route_risk_score": route_score,
                "in_safe_corridor": in_safe,
                "in_high_risk_zone": in_risk,
                "deviation_km": deviation,
            },
        }
        fusion_res, _ = api("/agents/risk-fusion/", fusion_payload, token)
        composite = float(fusion_res.get("composite_risk_score", 0.0))
        risk_level = fusion_res.get("risk_level", "LOW")
        triggered = fusion_res.get("triggered_rules", [])
        
        # F) Decision Agent
        dec_payload = {
            "trip_id": trip_id,
            "truck_id": truck_id,
            "composite_risk_score": composite,
            "risk_level": risk_level,
            "confidence": 0.9,
            "component_scores": {
                "behaviour": beh_score,
                "twin": twin_score,
                "route": route_score,
            },
            "triggered_rules": triggered,
            "fusion_method": "weighted_combination",
        }
        dec_res, _ = api("/agents/decision/", dec_payload, token)
        
        rc = R if composite > 0.6 else Y if composite > 0.4 else G
        print(f"  {DIM}Risk:{RST} {rc}{composite:.2f} [{risk_level}]{RST}")
        if dec_res.get("alert_id"):
             print(f"  {Y}⚠ Alert Generated! Rule Fired: {dec_res.get('rule_fired')}{RST}")
        print(f"  {DIM}Risk:{RST} {rc}{composite:.2f} [{risk_level}]{RST}")
        time.sleep(2)  # Tick every 2 seconds so UI updates smoothly

if __name__ == "__main__":
    run_live_simulation()
