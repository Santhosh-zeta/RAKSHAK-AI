import requests
import json
import random

class GeoSpatialService:
    """
    Service to interact with OpenStreetMap (OSRM) for route calculations.
    """
    OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving/"

    @classmethod
    def get_coordinates(cls, location_name):
        """
        Mock geocoding function. In production, use Nominatim API or Google Maps Geocoding API.
        For Hackathon: returns roughly accurate bounding box logic based on string matches
        or random gen within India.
        """
        location_name = location_name.lower()
        
        mock_cities = {
            "chennai": "80.2707,13.0827",
            "mumbai": "72.8777,19.0760",
            "delhi": "77.2090,28.6139",
            "bangalore": "77.5946,12.9716",
            "hyderabad": "78.4867,17.3850",
            "kolkata": "88.3639,22.5726"
        }
        
        for city, coords in mock_cities.items():
            if city in location_name:
                return coords
                
        # Fallback random coords in India
        lng = round(random.uniform(70.0, 90.0), 4)
        lat = round(random.uniform(10.0, 28.0), 4)
        return f"{lng},{lat}"

    @classmethod
    def calculate_route(cls, start_coords, dest_coords):
        """
        Calls OSRM to get driving distance, duration, and full coordinate geometry.
        """
        # OSRM expects: {longitude},{latitude};{longitude},{latitude}
        try:
            url = f"{cls.OSRM_BASE_URL}{start_coords};{dest_coords}?overview=full&geometries=geojson"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                route = data["routes"][0]
                return {
                    "distance_meters": route.get("distance", 0),
                    "duration_seconds": route.get("duration", 0),
                    "geometry": route.get("geometry", {}),
                    "success": True
                }
            return {"success": False, "error": "No route found"}
            
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def calculate_baseline_risk(cls, distance_meters, start_name, dest_name):
        """
        Mock baseline risk calculator.
        Longer distances = higher base risk.
        Specific keywords = higher base risk.
        """
        risk = 10.0 # Base minimum
        
        # Add risk for distance (1 risk point per 100km)
        risk += (distance_meters / 1000) / 100
        
        high_risk_zones = ["highway 44", "ghat", "forest", "border"]
        query = f"{start_name} {dest_name}".lower()
        
        for zone in high_risk_zones:
            if zone in query:
                risk += 15.0
                
        return min(100.0, round(risk, 2))
