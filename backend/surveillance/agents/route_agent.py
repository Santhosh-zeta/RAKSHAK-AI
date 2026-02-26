"""
RAKSHAK AI - Route Intelligence Agent
Validates GPS position against safe corridors and high-risk zones.
Uses Shapely geometry from AI-models/route_model.pkl.
Publishes RouteOutput to rakshak.route.output
"""

import asyncio
import json
import os
import math
from datetime import datetime
from typing import List, Optional, Dict, Any

import joblib
import redis.asyncio as aioredis
from pydantic import BaseModel
from shapely.geometry import Point, Polygon, MultiPolygon
import structlog


class RouteOutput(BaseModel):
    truck_id: str
    timestamp: str
    gps_lat: float
    gps_lon: float
    in_safe_corridor: bool
    deviation_km: float
    in_high_risk_zone: bool
    high_risk_zone_name: Optional[str]
    route_risk_score: float          # 0.0 to 1.0
    time_multiplier: float           # 1.0 or 1.5 for night hours
    nearest_corridor_name: Optional[str]


class RouteAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.model_path = os.path.join(
            os.path.dirname(__file__), "..", "ai_models", "route_model.pkl"
        )
        self.input_channel = "rakshak.twin.output"
        self.output_channel = "rakshak.route.output"
        self.redis = None
        self.running = False
        self.safe_corridors: List[dict] = []   # [{name, polygon: Polygon}]
        self.risk_zones: List[dict] = []       # [{name, polygon: Polygon}]
        self.night_hours = set(range(22, 24)) | set(range(0, 6))
        self.logger = structlog.get_logger().bind(agent="route_agent")

    async def start(self):
        """Initialize the route agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        # Load route geometry model
        try:
            model_data = joblib.load(self.model_path)
            
            # Load safe corridors
            self.safe_corridors = []
            for corridor_data in model_data.get("safe_corridors", []):
                coords = corridor_data["coordinates"]
                # Convert to Shapely Polygon (lon, lat format)
                polygon = Polygon([(lon, lat) for lon, lat in coords])
                self.safe_corridors.append({
                    "name": corridor_data["name"],
                    "polygon": polygon
                })
            
            # Load risk zones
            self.risk_zones = []
            for zone_data in model_data.get("risk_zones", []):
                coords = zone_data["coordinates"]
                # Convert to Shapely Polygon (lon, lat format)
                polygon = Polygon([(lon, lat) for lon, lat in coords])
                self.risk_zones.append({
                    "name": zone_data["name"],
                    "polygon": polygon
                })
                
            self.logger.info(f"Loaded route model with {len(self.safe_corridors)} corridors and {len(self.risk_zones)} risk zones")
            
        except FileNotFoundError:
            self.logger.warning("Route model not found, loading default geometry")
            await self._load_default_geometry()
        except Exception as e:
            self.logger.error("Error loading route model", error=str(e))
            await self._load_default_geometry()
        
        self.running = True
        self.logger.info(f"Route agent started with {len(self.safe_corridors)} corridors and {len(self.risk_zones)} risk zones")

    async def _load_default_geometry(self):
        """Load default safe corridors covering all major Indian logistics routes."""

        # Each corridor is a ±0.5° wide polygon centred on the route waypoints
        def _corridor_polygon(waypoints, width=0.5):
            """Build a rough envelope polygon around a list of (lat,lon) points."""
            lats = [p[0] for p in waypoints]
            lons = [p[1] for p in waypoints]
            min_lat, max_lat = min(lats) - width, max(lats) + width
            min_lon, max_lon = min(lons) - width, max(lons) + width
            return Polygon([
                (min_lon, min_lat), (max_lon, min_lat),
                (max_lon, max_lat), (min_lon, max_lat),
                (min_lon, min_lat),
            ])

        ROUTES = [
            ("NH-48 Delhi–Jaipur",       [(28.61,77.21),(28.41,76.99),(28.08,76.77),(27.54,76.20),(26.91,75.79)]),
            ("NH-48 Mumbai–Pune",         [(19.08,72.88),(18.97,73.12),(18.87,73.32),(18.52,73.86)]),
            ("NH-44 Bangalore–Chennai",   [(12.97,77.60),(12.70,77.90),(12.45,78.25),(12.20,78.55),(13.08,80.27)]),
            ("NH-16 Kolkata–Bhubaneswar", [(22.57,88.36),(22.20,88.15),(21.90,87.70),(21.47,86.92),(20.30,85.82)]),
            ("NH-44 Hyderabad–Nagpur",    [(17.39,78.49),(17.80,78.80),(18.44,79.13),(18.90,79.55),(21.15,79.09)]),
        ]

        self.safe_corridors = [
            {"name": name, "polygon": _corridor_polygon(wps)}
            for name, wps in ROUTES
        ]

        # Risk zones: known high-theft areas on these corridors
        risk_zone_defs = [
            ("Narela Industrial Area",    [(77.08,28.85),(77.12,28.85),(77.12,28.88),(77.08,28.88),(77.08,28.85)]),
            ("Tughlakabad Zone",          [(77.28,28.45),(77.35,28.45),(77.35,28.52),(77.28,28.52),(77.28,28.45)]),
            ("Khopoli High-Risk Stretch", [(73.05,18.90),(73.20,18.90),(73.20,19.00),(73.05,19.00),(73.05,18.90)]),
            ("Hosur Corridor Zone",       [(77.85,12.65),(77.95,12.65),(77.95,12.75),(77.85,12.75),(77.85,12.65)]),
            ("Mecheda NH-16 Stretch",     [(87.60,21.80),(87.80,21.80),(87.80,21.95),(87.60,21.95),(87.60,21.80)]),
        ]
        self.risk_zones = [
            {"name": name, "polygon": Polygon(coords)}
            for name, coords in risk_zone_defs
        ]


    async def stop(self):
        """Stop the route agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Route agent stopped")

    def _check_safe_corridor(self, point: Point) -> tuple[bool, float, Optional[str]]:
        """Check if point is within safe corridors"""
        # Check if point is within any corridor with 500m buffer
        for corridor in self.safe_corridors:
            # 0.0045 degrees ≈ 500m buffer
            if point.within(corridor["polygon"].buffer(0.0045)):
                return True, 0.0, corridor["name"]
        
        # Compute minimum distance to any corridor
        distances = []
        for corridor in self.safe_corridors:
            # Convert degrees to km (approximate)
            distance_deg = point.distance(corridor["polygon"])
            distance_km = distance_deg * 111.0  # 1 degree ≈ 111 km
            distances.append(distance_km)
        
        if distances:
            min_dist = min(distances)
            nearest_idx = distances.index(min_dist)
            nearest_name = self.safe_corridors[nearest_idx]["name"]
            return False, min_dist, nearest_name
        else:
            return False, 999.0, None

    def _check_risk_zones(self, point: Point) -> tuple[bool, Optional[str]]:
        """Check if point is within any high-risk zones"""
        for zone in self.risk_zones:
            if point.within(zone["polygon"]):
                return True, zone["name"]
        return False, None

    def _compute_time_multiplier(self, hour: int) -> float:
        """Compute time-based risk multiplier"""
        if hour in self.night_hours:
            return 1.5
        return 1.0

    def _compute_route_risk_score(self, in_safe: bool, deviation_km: float,
                                in_risk_zone: bool, multiplier: float) -> float:
        """Compute overall route risk score"""
        base_score = 0.0
        
        # Penalty for being outside safe corridors
        if not in_safe:
            base_score += min(deviation_km / 10.0, 0.6)
        
        # Penalty for being in risk zones
        if in_risk_zone:
            base_score += 0.3
        
        # Cap base score
        base_score = min(base_score, 1.0)
        
        # Apply time multiplier
        final_score = min(base_score * multiplier, 1.0)
        return final_score

    async def run(self):
        """Main processing loop listening to Redis channel"""
        if not self.running or not self.redis:
            self.logger.error("Agent not started or Redis not connected")
            return
        
        try:
            # Subscribe to input channel
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(self.input_channel)
            
            self.logger.info(f"Subscribed to {self.input_channel}")
            
            # Processing loop
            while self.running:
                try:
                    # Wait for message
                    message = await pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        # Parse JSON (TwinOutput format)
                        payload = json.loads(message['data'])
                        
                        truck_id = payload.get('truck_id')
                        gps_lat = payload.get('gps_lat')
                        gps_lon = payload.get('gps_lon')
                        timestamp = payload.get('timestamp')
                        
                        if not all([truck_id, gps_lat, gps_lon, timestamp]):
                            continue
                        
                        # Create Shapely point (lon, lat format)
                        point = Point(gps_lon, gps_lat)
                        
                        # Extract hour for time-based multiplier
                        hour = datetime.fromisoformat(timestamp).hour
                        
                        # Check route compliance
                        in_safe, deviation_km, corridor_name = self._check_safe_corridor(point)
                        in_risk, risk_zone_name = self._check_risk_zones(point)
                        multiplier = self._compute_time_multiplier(hour)
                        risk_score = self._compute_route_risk_score(
                            in_safe, deviation_km, in_risk, multiplier
                        )
                        
                        # Build RouteOutput
                        route_output = RouteOutput(
                            truck_id=truck_id,
                            timestamp=datetime.now().isoformat(),
                            gps_lat=gps_lat,
                            gps_lon=gps_lon,
                            in_safe_corridor=in_safe,
                            deviation_km=deviation_km,
                            in_high_risk_zone=in_risk,
                            high_risk_zone_name=risk_zone_name,
                            route_risk_score=risk_score,
                            time_multiplier=multiplier,
                            nearest_corridor_name=corridor_name
                        )
                        
                        # Publish to output channel
                        await self.redis.publish(
                            self.output_channel,
                            route_output.model_dump_json()
                        )
                        
                        # Store in Redis with TTL
                        status_key = f"route_status:{truck_id}"
                        await self.redis.setex(
                            status_key,
                            60,  # 60 seconds TTL
                            route_output.model_dump_json()
                        )
                        
                        # Log warnings for route violations
                        if not in_safe or in_risk:
                            self.logger.warning(
                                "Route violation detected",
                                truck_id=truck_id,
                                in_safe_corridor=in_safe,
                                deviation_km=deviation_km,
                                in_high_risk_zone=in_risk,
                                risk_zone_name=risk_zone_name,
                                route_risk_score=risk_score
                            )
                        else:
                            self.logger.debug(
                                "Route status normal",
                                truck_id=truck_id,
                                route_risk_score=risk_score
                            )
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.input_channel)


if __name__ == "__main__":
    agent = RouteAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())