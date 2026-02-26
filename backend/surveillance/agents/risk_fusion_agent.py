"""
RAKSHAK AI - Risk Fusion Agent
Aggregates behaviour, twin, and route signals.
Uses pgmpy Bayesian inference or weighted scoring fallback.
Publishes RiskOutput to rakshak.risk.output
"""

import asyncio
import json
import os
import math
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict

import numpy as np
import joblib
import redis.asyncio as aioredis
from pydantic import BaseModel
import structlog

try: 
    from pgmpy.inference import VariableElimination
    PGMPY_AVAILABLE = True
except ImportError: 
    PGMPY_AVAILABLE = False


class RiskOutput(BaseModel):
    truck_id: str
    timestamp: str
    incident_id: str                 # uuid4 string, generated per fusion event
    composite_risk_score: float      # 0.0 to 1.0
    risk_level: str                  # LOW / MEDIUM / HIGH / CRITICAL
    confidence: float                # 0.0 to 1.0 (product of quality factors)
    component_scores: Dict[str, float]  # {behaviour, twin, route, temporal}
    triggered_rules: List[str]
    fusion_method: str               # "bayesian" or "weighted_fallback"


class RiskFusionAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.model_path = "AI-models/risk_model.pkl"
        self.output_channel = "rakshak.risk.output"
        self.input_channels = ["rakshak.behaviour.output",
                              "rakshak.twin.output",
                              "rakshak.route.output"]
        self.redis = None
        self.running = False
        self.bn_model = None             # pgmpy BayesianNetwork or None
        self.bn_inference = None         # VariableElimination
        self.fallback_weights = {"behaviour": 0.35, "twin": 0.30,
                               "route": 0.25, "temporal": 0.10}
        self._signal_buffer: Dict[str, Dict] = {}  # truck_id -> {channel: {data, ts}}
        self._lock = asyncio.Lock()
        self.signal_staleness_s = 10.0  # reject signals older than this
        self.logger = structlog.get_logger().bind(agent="risk_fusion_agent")

    async def start(self):
        """Initialize the risk fusion agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        # Try to load the Bayesian Network model
        try:
            model = joblib.load(self.model_path)
            
            # Check if it's a valid Bayesian Network model
            if hasattr(model, "get_cpds") and PGMPY_AVAILABLE:
                self.bn_model = model
                self.bn_inference = VariableElimination(self.bn_model)
                self.logger.info("Bayesian Network loaded")
            else:
                self.bn_model = None
                self.logger.info("Using weighted fallback scoring")
        except FileNotFoundError:
            self.logger.warning("Risk model not found, using weighted fallback scoring")
            self.bn_model = None
        except Exception as e:
            self.logger.error("Error loading risk model", error=str(e))
            self.bn_model = None
        
        self.running = True
        self.logger.info("Risk Fusion agent started")

    async def stop(self):
        """Stop the risk fusion agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Risk Fusion agent stopped")

    def _quality_factor(self, age_seconds: float) -> float:
        """Compute quality factor based on data age"""
        return math.exp(-0.01 * age_seconds)

    def _get_temporal_score(self) -> float:
        """Get temporal risk score based on time of day"""
        hour = datetime.now().hour
        if hour in range(22, 24) or hour in range(0, 6):
            return 0.8
        elif hour in range(6, 9) or hour in range(18, 22):
            return 0.4
        return 0.1

    def _classify_risk_level(self, score: float) -> str:
        """Classify risk level based on score"""
        if score >= 0.85:
            return "CRITICAL"
        elif score >= 0.65:
            return "HIGH"
        elif score >= 0.45:
            return "MEDIUM"
        return "LOW"

    def _get_triggered_rules(self, signals: dict, score: float) -> List[str]:
        """Get list of triggered rules based on signals and score"""
        rules = []
        
        if signals.get("behaviour", {}).get("loitering_detected"): 
            rules.append("LOITERING_DETECTED")
            
        if (signals.get("twin", {}).get("door_state") == "OPEN" and 
            not signals.get("twin", {}).get("driver_rfid_scanned")):
            rules.append("DOOR_OPEN_NO_RFID")
            
        if not signals.get("route", {}).get("in_safe_corridor"):
            rules.append("GEOFENCE_VIOLATION")
            
        if signals.get("route", {}).get("in_high_risk_zone"):
            rules.append("HIGH_RISK_ZONE_ENTRY")
            
        if score >= 0.85:
            rules.append("CRITICAL_THRESHOLD_BREACH")
            
        return rules

    async def _weighted_fusion(self, signals: dict, data_ages: dict) -> tuple[float, float, str]:
        """Perform weighted fusion using fallback method"""
        # Extract component scores
        behaviour_score = signals.get("behaviour", {}).get("anomaly_score", 0.0)
        twin_score = signals.get("twin", {}).get("deviation_score", 0.0)
        route_score = signals.get("route", {}).get("route_risk_score", 0.0)
        temporal_score = self._get_temporal_score()
        
        # Compute quality-adjusted weights
        adj_weights = {}
        for key, base_w in self.fallback_weights.items():
            age = data_ages.get(key, 0.0)
            adj_weights[key] = base_w * self._quality_factor(age)
        
        total_weight = sum(adj_weights.values())
        
        # Calculate weighted composite score
        if total_weight > 0:
            composite = (adj_weights["behaviour"] * behaviour_score +
                        adj_weights["twin"] * twin_score +
                        adj_weights["route"] * route_score +
                        adj_weights["temporal"] * temporal_score) / total_weight
        else:
            composite = 0.0
        
        # Calculate confidence as product of quality factors
        confidence = 1.0
        for age in data_ages.values():
            confidence *= self._quality_factor(age)
        
        # Prepare component scores
        component_scores = {
            "behaviour": behaviour_score,
            "twin": twin_score,
            "route": route_score,
            "temporal": temporal_score
        }
        
        return min(composite, 1.0), confidence, "weighted_fallback"

    async def _bayesian_fusion(self, signals: dict) -> tuple[float, float, str]:
        """Perform Bayesian fusion using pgmpy"""
        # Map signal scores to categorical evidence
        # Behaviour: critical if score >= 0.7, suspicious if >= 0.4, normal otherwise
        behaviour_score = signals.get("behaviour", {}).get("anomaly_score", 0.0)
        if behaviour_score >= 0.7:
            behaviour_cat = "critical"
        elif behaviour_score >= 0.4:
            behaviour_cat = "suspicious"
        else:
            behaviour_cat = "normal"
        
        # Twin: critical if score >= 0.7, degraded if >= 0.4, nominal otherwise
        twin_score = signals.get("twin", {}).get("deviation_score", 0.0)
        if twin_score >= 0.7:
            twin_cat = "critical"
        elif twin_score >= 0.4:
            twin_cat = "degraded"
        else:
            twin_cat = "nominal"
        
        # Route: major_off if deviation >= 2km, minor_off if >= 0.5km, on_route otherwise
        route_deviation = signals.get("route", {}).get("deviation_km", 0.0)
        if route_deviation >= 2.0:
            route_cat = "major_off"
        elif route_deviation >= 0.5:
            route_cat = "minor_off"
        else:
            route_cat = "on_route"
        
        # Time: night if in night hours, day otherwise
        hour = datetime.now().hour
        night_hours = set(range(22, 24)) | set(range(0, 6))
        time_cat = "night" if hour in night_hours else "day"
        
        # Build evidence dict mapping node names to categories
        # Note: We assume the BN model has nodes named appropriately
        evidence = {
            "BehaviourRisk": behaviour_cat,
            "TwinDeviation": twin_cat,
            "RouteCompliance": route_cat,
            "TimeOfDay": time_cat
        }
        
        try:
            # Run inference to get TheftRisk probabilities
            result = self.bn_inference.query(["TheftRisk"], evidence=evidence)
            
            # Map categorical result to float score
            weights = {"low": 0.0, "medium": 0.33, "high": 0.67, "critical": 1.0}
            score = sum(p * weights[cat] for cat, p in zip(
                result.state_names["TheftRisk"], result.values))
            
            # Confidence is the highest probability among all outcomes
            confidence = max(result.values)
            
            return score, confidence, "bayesian"
        except Exception as e:
            self.logger.warning("Bayesian inference failed, falling back to weighted scoring", error=str(e))
            # If Bayesian inference fails, fall back to weighted scoring
            # For this fallback, we'll use the same data to compute weighted score
            data_ages = {k: 0.0 for k in ["behaviour", "twin", "route"]}  # Assume fresh data
            signals_dict = {
                "behaviour": {"anomaly_score": behaviour_score},
                "twin": {"deviation_score": twin_score},
                "route": {"route_risk_score": signals.get("route", {}).get("route_risk_score", 0.0)}
            }
            return await self._weighted_fusion(signals_dict, data_ages)

    async def run(self):
        """Main processing loop listening to Redis channels"""
        if not self.running or not self.redis:
            self.logger.error("Agent not started or Redis not connected")
            return
        
        try:
            # Create async Redis pubsub subscribed to ALL 3 input channels simultaneously
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*self.input_channels)
            
            self.logger.info(f"Subscribed to {', '.join(self.input_channels)}")
            
            # Processing loop
            while self.running:
                try:
                    # Wait for message
                    message = await pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        # Identify which channel it came from
                        channel = message['channel'].decode('utf-8')
                        
                        # Parse JSON payload
                        payload = json.loads(message['data'])
                        truck_id = payload.get('truck_id')
                        
                        if not truck_id:
                            continue
                        
                        # async with self._lock:
                        async with self._lock:
                            # Update self._signal_buffer[truck_id][channel] = {
                            #     "data": payload, "received_at": time.time()
                            # }
                            if truck_id not in self._signal_buffer:
                                self._signal_buffer[truck_id] = {}
                            
                            self._signal_buffer[truck_id][channel] = {
                                "data": payload,
                                "received_at": time.time()
                            }
                            
                            # Check if all 3 signals present for this truck_id
                            channel_mapping = {
                                "rakshak.behaviour.output": "behaviour",
                                "rakshak.twin.output": "twin",
                                "rakshak.route.output": "route"
                            }
                            
                            available_channels = list(self._signal_buffer[truck_id].keys())
                            mapped_channels = [channel_mapping.get(ch) for ch in available_channels]
                            
                            if all(ch in mapped_channels for ch in ["behaviour", "twin", "route"]):
                                # Check all signals fresher than self.signal_staleness_s
                                current_time = time.time()
                                all_fresh = True
                                for ch_data in self._signal_buffer[truck_id].values():
                                    if current_time - ch_data["received_at"] > self.signal_staleness_s:
                                        all_fresh = False
                                        break
                                
                                if all_fresh:
                                    # Prepare signals dictionary
                                    signals = {}
                                    data_ages = {}
                                    
                                    for orig_ch, mapped_ch in channel_mapping.items():
                                        if orig_ch in self._signal_buffer[truck_id]:
                                            ch_data = self._signal_buffer[truck_id][orig_ch]
                                            signals[mapped_ch] = ch_data["data"]
                                            data_ages[mapped_ch] = current_time - ch_data["received_at"]
                                    
                                    # Perform fusion
                                    if self.bn_model:
                                        score, confidence, method = await self._bayesian_fusion(signals)
                                    else:
                                        score, confidence, method = await self._weighted_fusion(signals, data_ages)
                                    
                                    # Get triggered rules
                                    triggered = self._get_triggered_rules(signals, score)
                                    
                                    # Build RiskOutput
                                    risk_output = RiskOutput(
                                        truck_id=truck_id,
                                        timestamp=datetime.now().isoformat(),
                                        incident_id=str(uuid.uuid4()),
                                        composite_risk_score=score,
                                        risk_level=self._classify_risk_level(score),
                                        confidence=confidence,
                                        component_scores={
                                            "behaviour": signals.get("behaviour", {}).get("anomaly_score", 0.0),
                                            "twin": signals.get("twin", {}).get("deviation_score", 0.0),
                                            "route": signals.get("route", {}).get("route_risk_score", 0.0),
                                            "temporal": self._get_temporal_score()
                                        },
                                        triggered_rules=triggered,
                                        fusion_method=method
                                    )
                                    
                                    # Publish to output channel
                                    await self.redis.publish(
                                        self.output_channel,
                                        risk_output.model_dump_json()
                                    )
                                    
                                    # Write Redis key: risk_score:{truck_id} = score, TTL 60s
                                    risk_key = f"risk_score:{truck_id}"
                                    await self.redis.setex(risk_key, 60, str(score))
                                    
                                    # Log risk_level and composite_score
                                    self.logger.info(
                                        "Risk assessment computed",
                                        truck_id=truck_id,
                                        risk_level=risk_output.risk_level,
                                        composite_score=risk_output.composite_risk_score,
                                        method=method,
                                        triggered_rules=triggered
                                    )
                                    
                                    # Clear the processed signals
                                    del self._signal_buffer[truck_id]
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(*self.input_channels)


if __name__ == "__main__":
    agent = RiskFusionAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())
    god