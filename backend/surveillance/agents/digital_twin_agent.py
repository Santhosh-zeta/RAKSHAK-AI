"""
RAKSHAK AI - Digital Twin Agent
Maintains real-time virtual replica of each truck via IoT telemetry.
Detects weight, door, GPS, and signal deviations.
Publishes TwinOutput to rakshak.twin.output
"""

import asyncio
import json
import os
import math
from datetime import datetime
from typing import List, Optional, Dict

import redis.asyncio as aioredis
from pydantic import BaseModel
import structlog


class IoTTelemetry(BaseModel):
    truck_id: str
    timestamp: str
    gps_lat: float
    gps_lon: float
    door_state: str                  # "OPEN" or "CLOSED"
    cargo_weight_kg: float
    engine_on: bool
    driver_rfid_scanned: bool
    iot_signal_strength: float       # 0.0 to 1.0


class TwinOutput(BaseModel):
    truck_id: str
    timestamp: str
    gps_lat: float
    gps_lon: float
    door_state: str
    cargo_weight_kg: float
    engine_on: bool
    driver_rfid_scanned: bool
    deviation_score: float           # 0.0 to 1.0
    deviations: List[str]            # human-readable list of detected issues
    twin_status: str                 # "NOMINAL", "DEGRADED", "CRITICAL"
    iot_signal_fresh: bool


class DigitalTwinAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.input_channel = "rakshak.iot.telemetry"
        self.output_channel = "rakshak.twin.output"
        self.twin_state_ttl = 300        # seconds
        self.redis = None
        self.running = False
        self._lock = asyncio.Lock()
        self._twin_states: Dict[str, dict] = {}   # in-memory state per truck
        self.logger = structlog.get_logger().bind(agent="digital_twin_agent")

    async def start(self):
        """Initialize the digital twin agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        # Load baselines for all known trucks
        try:
            pattern = "twin_baseline:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key.decode('utf-8'))
            
            for key in keys:
                truck_id = key.split(":")[1]
                baseline_data = await self.redis.get(key)
                if baseline_data:
                    baseline = json.loads(baseline_data)
                    self._twin_states[truck_id] = {"baseline": baseline}
                    self.logger.info(f"Loaded baseline for truck {truck_id}")
        except Exception as e:
            self.logger.warning("Could not load baselines", error=str(e))
        
        self.running = True
        self.logger.info("Digital Twin agent started")

    async def stop(self):
        """Stop the digital twin agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Digital Twin agent stopped")

    async def _get_baseline(self, truck_id: str) -> dict:
        """Get baseline configuration for a truck"""
        # Check in-memory cache first
        if truck_id in self._twin_states and "baseline" in self._twin_states[truck_id]:
            return self._twin_states[truck_id]["baseline"]

        # Try to get from Redis (only if Redis is connected)
        if self.redis is not None:
            try:
                key = f"twin_baseline:{truck_id}"
                baseline_data = await self.redis.get(key)
                if baseline_data:
                    baseline = json.loads(baseline_data)
                    # Cache in memory
                    if truck_id not in self._twin_states:
                        self._twin_states[truck_id] = {}
                    self._twin_states[truck_id]["baseline"] = baseline
                    return baseline
            except Exception as e:
                self.logger.warning(f"Error loading baseline for {truck_id}", error=str(e))

        # Default baseline (used when Redis is unavailable or no key exists)
        default_baseline = {
            "expected_weight_kg": 2000.0,
            "expected_door_state": "CLOSED",
            "planned_route_center": {"lat": 28.6139, "lon": 77.2090},
            "max_deviation_km": 0.5
        }

        # Cache the default in memory
        if truck_id not in self._twin_states:
            self._twin_states[truck_id] = {}
        self._twin_states[truck_id]["baseline"] = default_baseline

        return default_baseline

    def _compute_gps_deviation_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Compute distance between two GPS coordinates using Haversine formula"""
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        distance_km = R * c
        return distance_km

    async def _detect_deviations(self, telemetry: IoTTelemetry, baseline: dict) -> tuple[List[str], float]:
        """Detect deviations from baseline and compute deviation score"""
        deviations = []
        score_components = []
        
        # Weight deviation check
        expected_weight = baseline.get("expected_weight_kg", 2000.0)
        weight_delta = abs(telemetry.cargo_weight_kg - expected_weight)
        if weight_delta > 50:
            deviations.append(f"Cargo weight deviation: {weight_delta:.1f}kg")
            score_components.append(min(weight_delta / 500.0, 1.0))
        
        # Door security check
        if (telemetry.door_state == "OPEN" and 
            not telemetry.engine_on and 
            not telemetry.driver_rfid_scanned):
            deviations.append("Door open without RFID authorization")
            score_components.append(0.8)
        
        # GPS route deviation check
        route_center = baseline.get("planned_route_center", {"lat": 28.6139, "lon": 77.2090})
        max_deviation_km = baseline.get("max_deviation_km", 0.5)
        
        deviation_km = self._compute_gps_deviation_km(
            telemetry.gps_lat, telemetry.gps_lon,
            route_center["lat"], route_center["lon"]
        )
        
        if deviation_km > max_deviation_km:
            deviations.append(f"GPS off-route by {deviation_km:.2f}km")
            score_components.append(min(deviation_km / 5.0, 1.0))
        
        # Signal quality check
        if telemetry.iot_signal_strength < 0.3:
            deviations.append("Weak IoT signal — possible jamming")
            score_components.append(0.4)
        
        # Calculate overall deviation score
        if score_components:
            deviation_score = min(sum(score_components) / len(score_components), 1.0)
        else:
            deviation_score = 0.0
        
        return deviations, deviation_score

    def _classify_status(self, score: float) -> str:
        """Classify twin status based on deviation score"""
        if score >= 0.7:
            return "CRITICAL"
        elif score >= 0.4:
            return "DEGRADED"
        else:
            return "NOMINAL"

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
                        # Parse JSON into IoTTelemetry
                        payload = json.loads(message['data'])
                        telemetry = IoTTelemetry(**payload)
                        
                        # Get baseline configuration
                        baseline = await self._get_baseline(telemetry.truck_id)
                        
                        # Detect deviations
                        async with self._lock:
                            deviations, deviation_score = await self._detect_deviations(
                                telemetry, baseline
                            )
                        
                        # Classify status
                        status = self._classify_status(deviation_score)
                        
                        # Check signal freshness
                        telemetry_time = datetime.fromisoformat(telemetry.timestamp)
                        current_time = datetime.now()
                        time_diff = (current_time - telemetry_time).total_seconds()
                        iot_signal_fresh = time_diff < 60
                        
                        # Build TwinOutput
                        twin_output = TwinOutput(
                            truck_id=telemetry.truck_id,
                            timestamp=datetime.now().isoformat(),
                            gps_lat=telemetry.gps_lat,
                            gps_lon=telemetry.gps_lon,
                            door_state=telemetry.door_state,
                            cargo_weight_kg=telemetry.cargo_weight_kg,
                            engine_on=telemetry.engine_on,
                            driver_rfid_scanned=telemetry.driver_rfid_scanned,
                            deviation_score=deviation_score,
                            deviations=deviations,
                            twin_status=status,
                            iot_signal_fresh=iot_signal_fresh
                        )
                        
                        # Publish to output channel
                        await self.redis.publish(
                            self.output_channel,
                            twin_output.model_dump_json()
                        )
                        
                        # Store in Redis with TTL
                        state_key = f"twin_state:{telemetry.truck_id}"
                        await self.redis.setex(
                            state_key,
                            self.twin_state_ttl,
                            twin_output.model_dump_json()
                        )
                        
                        # Log warnings for non-nominal status
                        if status != "NOMINAL":
                            self.logger.warning(
                                "Twin deviation detected",
                                truck_id=telemetry.truck_id,
                                status=status,
                                deviation_score=deviation_score,
                                deviations=deviations
                            )
                        else:
                            self.logger.debug(
                                "Twin status nominal",
                                truck_id=telemetry.truck_id,
                                deviation_score=deviation_score
                            )
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.input_channel)


if __name__ == "__main__":
    agent = DigitalTwinAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())