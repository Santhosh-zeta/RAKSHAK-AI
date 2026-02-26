"""
RAKSHAK AI - Behaviour Analysis Agent
Runs Isolation Forest anomaly detection on perception tracks.
Detects loitering, crowd anomalies, and suspicious movement.
Publishes BehaviourOutput to rakshak.behaviour.output
"""

import asyncio
import json
import os
import math
from datetime import datetime
from typing import List, Optional

import numpy as np
import joblib
import redis.asyncio as aioredis
from pydantic import BaseModel
import structlog


class BehaviourOutput(BaseModel):
    truck_id: str
    timestamp: str
    anomaly_score: float        # 0.0 (normal) to 1.0 (critical anomaly)
    is_anomaly: bool
    flagged_track_ids: List[int]
    loitering_detected: bool
    loitering_duration_s: float
    crowd_anomaly: bool
    raw_scores: dict            # {track_id: score}


class BehaviourAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.model_path = os.path.join(
            os.path.dirname(__file__), "..", "ai_models", "behavior_model.pkl"
        )
        self.input_channel = "rakshak.perception.output"
        self.output_channel = "rakshak.behaviour.output"
        self.redis = None
        self.model = None             # Isolation Forest
        self.running = False
        self.loitering_threshold_s = 30.0
        self.anomaly_threshold = 0.6  # scores above this trigger is_anomaly=True
        self.logger = structlog.get_logger().bind(agent="behaviour_agent")

    async def start(self):
        """Initialize the behaviour agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        # Load model
        try:
            self.model = joblib.load(self.model_path)
            self.logger.info("Behaviour model loaded successfully")
        except FileNotFoundError:
            self.logger.warning("Model not found, using heuristic fallback")
            self.model = None
        except Exception as e:
            self.logger.error("Error loading model", error=str(e))
            self.model = None
        
        self.running = True
        self.logger.info("Behaviour agent started")

    async def stop(self):
        """Stop the behaviour agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Behaviour agent stopped")

    def _build_features(self, track: dict) -> np.ndarray:
        """Extract features from track for anomaly detection"""
        # Extract track properties
        dwell_seconds = track.get('dwell_seconds', 0.0)
        velocity = track.get('velocity', {'dx': 0.0, 'dy': 0.0})
        dx = velocity.get('dx', 0.0)
        dy = velocity.get('dy', 0.0)
        confidence = track.get('confidence', 0.0)
        
        # Compute derived features
        velocity_magnitude = math.sqrt(dx**2 + dy**2)
        is_near_door = 1.0 if dwell_seconds > 20 else 0.0
        time_of_day_hour = float(datetime.now().hour)
        
        # Return feature vector
        return np.array([[dwell_seconds, velocity_magnitude, confidence,
                         is_near_door, time_of_day_hour]])

    def _heuristic_score(self, track: dict) -> float:
        """Simple rule-based scoring fallback when no model is available"""
        score = 0.0
        dwell_seconds = track.get('dwell_seconds', 0.0)
        velocity = track.get('velocity', {'dx': 0.0, 'dy': 0.0})
        dx = velocity.get('dx', 0.0)
        dy = velocity.get('dy', 0.0)
        velocity_magnitude = math.sqrt(dx**2 + dy**2)
        hour = datetime.now().hour
        
        # Loitering detection
        if dwell_seconds > 30:
            score += 0.4
        if dwell_seconds > 60:
            score += 0.3
            
        # Low velocity + long dwell = suspicious
        if velocity_magnitude < 0.5 and dwell_seconds > 20:
            score += 0.2
            
        # Night time suspicious activity
        if hour >= 22 or hour <= 5:
            score += 0.1
            
        return min(score, 1.0)

    def _normalize_if_score(self, raw_scores: np.ndarray) -> np.ndarray:
        """Normalize Isolation Forest scores to [0, 1] range"""
        if len(raw_scores) == 0:
            return np.array([])
            
        # Isolation Forest decision_function returns negative values for anomalies
        # More negative = more anomalous
        min_score = np.min(raw_scores)
        max_score = np.max(raw_scores)
        
        # Avoid division by zero
        if min_score == max_score:
            return np.zeros_like(raw_scores)
        
        # Normalize: (min - scores) / (min - max) 
        # This maps most negative (anomalous) to 1.0, least negative (normal) to 0.0
        normalized = (min_score - raw_scores) / (min_score - max_score)
        
        # Clip to [0, 1] range
        return np.clip(normalized, 0.0, 1.0)

    async def _process_perception_output(self, payload: dict) -> BehaviourOutput:
        """Process perception output and detect anomalous behavior"""
        truck_id = payload.get('truck_id', 'TRK-001')
        tracks = payload.get('tracks', [])
        timestamp = datetime.now().isoformat()
        
        # Process each track
        raw_scores = {}
        for track in tracks:
            track_id = track.get('track_id')
            if track_id is None:
                continue
                
            features = self._build_features(track)
            
            if self.model is not None:
                # Use trained Isolation Forest model
                try:
                    raw_score = self.model.decision_function(features)[0]
                    # Normalize the score to [0, 1]
                    normalized_score = self._normalize_if_score(np.array([raw_score]))[0]
                except Exception as e:
                    self.logger.warning("Model prediction failed, using heuristic", error=str(e))
                    normalized_score = self._heuristic_score(track)
            else:
                # Use heuristic scoring
                normalized_score = self._heuristic_score(track)
            
            raw_scores[track_id] = float(normalized_score)
        
        # Determine flagged tracks
        flagged_track_ids = [
            track_id for track_id, score in raw_scores.items()
            if score > self.anomaly_threshold
        ]
        
        # Compute overall metrics
        overall_anomaly_score = max(raw_scores.values()) if raw_scores else 0.0
        
        # Loitering detection
        loitering_tracks = [
            track for track in tracks
            if track.get('dwell_seconds', 0.0) > self.loitering_threshold_s
        ]
        
        loitering_detected = (
            len(loitering_tracks) > 0 and 
            any(track_id in flagged_track_ids for track_id in [t.get('track_id') for t in loitering_tracks])
        )
        
        loitering_duration_s = max(
            [track.get('dwell_seconds', 0.0) for track in loitering_tracks]
        ) if loitering_tracks else 0.0
        
        # Crowd anomaly detection
        crowd_anomaly = len(tracks) > 4 and overall_anomaly_score > 0.5
        
        # Final anomaly determination
        is_anomaly = overall_anomaly_score > self.anomaly_threshold
        
        # Create output
        return BehaviourOutput(
            truck_id=truck_id,
            timestamp=timestamp,
            anomaly_score=float(overall_anomaly_score),
            is_anomaly=is_anomaly,
            flagged_track_ids=flagged_track_ids,
            loitering_detected=loitering_detected,
            loitering_duration_s=float(loitering_duration_s),
            crowd_anomaly=crowd_anomaly,
            raw_scores=raw_scores
        )

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
                        # Parse JSON payload
                        payload = json.loads(message['data'])
                        
                        # Process perception output
                        output = await self._process_perception_output(payload)
                        
                        # Publish behaviour output
                        await self.redis.publish(
                            self.output_channel,
                            output.model_dump_json()
                        )
                        
                        # Log based on anomaly status
                        if output.is_anomaly:
                            self.logger.warning(
                                "Anomaly detected",
                                truck_id=output.truck_id,
                                anomaly_score=output.anomaly_score,
                                flagged_tracks=len(output.flagged_track_ids)
                            )
                        else:
                            self.logger.debug(
                                "Normal behavior",
                                truck_id=output.truck_id,
                                anomaly_score=output.anomaly_score
                            )
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.input_channel)


if __name__ == "__main__":
    agent = BehaviourAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())