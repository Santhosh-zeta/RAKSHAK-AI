import os
import django

# Setup Django environment so we can import services
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rakshak.settings")
django.setup()

from surveillance.services.map_service import GeoSpatialService
from simulate_truck import RouteSimulator

def run_test():
    trip_id = "ce6c07de-5060-4919-8bd6-69580cf1b3f8"
    start = "80.2707,13.0827"
    dest = "77.5946,12.9716"
    
    print(f"Fetching route from OSRM for {start} to {dest}...")
    route_info = GeoSpatialService.calculate_route(start, dest)
    
    if route_info.get("success"):
        print("Route fetched successfully!")
        coords = route_info["geometry"]["coordinates"]
        print(f"Total points in route: {len(coords)}")
        
        # We don't want to run the full simulation forever in this test, let's just do 5 steps
        coords = coords[:5] 
        
        sim = RouteSimulator("http://127.0.0.1:8000", trip_id, coords)
        print("Starting Simulation...")
        sim.run_simulation(tick_seconds=1)
    else:
        print("Failed to get route:", route_info.get("error"))

if __name__ == "__main__":
    run_test()
