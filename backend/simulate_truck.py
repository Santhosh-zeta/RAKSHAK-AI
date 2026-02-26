import time
import requests
import random
import math

class RouteSimulator:
    """
    Simulates a truck moving along an OSRM geometry path, pushing GPS 
    and IoT telemetry to the RAKSHAK Backend.
    """
    
    def __init__(self, backend_url, trip_id, geometry_coords):
        self.backend_url = backend_url
        self.trip_id = trip_id
        self.coords = geometry_coords # List of [lon, lat] points
        self.current_step = 0
        self.total_steps = len(self.coords)
        
    def _calculate_heading(self, p1, p2):
        """Calculate compass bearing between two points"""
        lon1, lat1 = map(math.radians, p1)
        lon2, lat2 = map(math.radians, p2)
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        brng = math.degrees(math.atan2(y, x))
        return (brng + 360) % 360

    def step(self):
        """Moves truck one step forward and pushes data"""
        if self.current_step >= self.total_steps:
            print("Trip Complete!")
            return False

        # Get current and next coords to compute heading
        curr_pt = self.coords[self.current_step]
        lon, lat = curr_pt[0], curr_pt[1]
        
        heading = 0.0
        if self.current_step < self.total_steps - 1:
            next_pt = self.coords[self.current_step + 1]
            heading = self._calculate_heading(curr_pt, next_pt)
            
        # Fluctuate speed slightly
        speed = round(random.uniform(50.0, 75.0), 1)
        
        # Build Telemetry Payload
        payload = {
            "trip": self.trip_id, # Must match DRF ForeignKey expectation
            "latitude": lat,
            "longitude": lon,
            "speed_kmh": speed,
            "heading": heading,
            "engine_status": True,
            "door_sealed": True
        }
        
        try:
            url = f"{self.backend_url}/api/gps-logs/"
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 201:
                print(f"[Trip] Ping Sent -> Lat: {lat:.4f} | Lon: {lon:.4f} | Spd: {speed}km/h")
            else:
                print(f"Failed to push log: {r.text}")
        except Exception as e:
            print(f"Connection error: {e}")

        self.current_step += 1
        return True

    def run_simulation(self, tick_seconds=2):
        print(f"Starting journey simulation for Trip {self.trip_id}...")
        while self.step():
            time.sleep(tick_seconds)


if __name__ == "__main__":
    # Example usage (Replace with real trip_id from DB):
    # TRUCK UUID = 'your-trip-uuid'
    # COORDS = [[77.2090,28.6139], [77.2100,28.6140], ...]
    # sim = RouteSimulator("http://localhost:8000", TRUCK_UUID, COORDS)
    # sim.run_simulation()
    pass
