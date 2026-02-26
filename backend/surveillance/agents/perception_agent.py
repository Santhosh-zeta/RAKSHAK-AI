

import asyncio
import base64
import json
import os
import time
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np
import torch
from deep_sort_realtime.deepsort_tracker import DeepSort
from pydantic import BaseModel
from ultralytics import YOLO
import redis.asyncio as aioredis
import structlog


class Velocity(BaseModel):
    dx: float
    dy: float


class Track(BaseModel):
    track_id: int
    class_name: str
    
    confidence: float
    bbox: List[int]        # [x1, y1, x2, y2]
    velocity: Velocity
    dwell_seconds: float


class PerceptionOutput(BaseModel):
    truck_id: str
    frame_id: int
    timestamp: str         # ISO format
    tracks: List[Track]
    scene_tags: List[str]  # e.g. ["night", "no_driver_present"]


class PerceptionAgent:
    def __init__(self):
        self.truck_id = os.getenv("TRUCK_ID", "TRK-001")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.model_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self.input_channel = "rakshak.camera.frames"
        self.output_channel = "rakshak.perception.output"
        self.conf_threshold = 0.5
        self.redis: Optional[aioredis.Redis] = None
        self.tracker = DeepSort(max_age=30)
        self.model = None
        self.track_history: dict = {}   # track_id -> list of (x,y) centroids
        self.track_first_seen: dict = {} # track_id -> timestamp float
        self.frame_id: int = 0
        self.running: bool = False
        self.logger = structlog.get_logger().bind(agent="perception_agent")

    async def start(self):
        """Initialize the perception agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        # Load YOLO model
        self.model = YOLO(self.model_path)
        
        # Configure device
        if torch.cuda.is_available():
            self.model.to('cuda')
            self.logger.info("GPU enabled")
        else:
            self.logger.warning("GPU unavailable, using CPU")
            self.conf_threshold = 0.4  # Lower threshold for CPU performance
        
        self.running = True
        self.logger.info("Perception agent started")

    async def stop(self):
        """Stop the perception agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Perception agent stopped")

    def _compute_scene_tags(self, tracks: List[Track], hour: int) -> List[str]:
        """Compute scene tags based on tracks and time"""
        tags = []
        
        # Night time detection
        if hour < 6 or hour >= 22:
            tags.append("night")
        
        # No driver present
        if not any(t.class_name == "person" for t in tracks):
            tags.append("no_driver_present")
        
        # Loitering detection
        if any(t.dwell_seconds > 30 for t in tracks):
            tags.append("loitering_detected")
        
        # Crowd detection
        if len(tracks) > 3:
            tags.append("crowd_detected")
        
        return tags

    def _process_frame(self, frame_bytes: bytes) -> List[Track]:
        """Process a single frame and return tracks"""
        # Decode bytes to numpy array
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return []
        
        # Run YOLO detection
        results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)
        
        # Extract detections
        detections = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    # Only track persons and vehicles for security purposes
                    if class_name in ['person', 'car', 'truck', 'bus', 'motorcycle']:
                        detections.append(([x1, y1, x2, y2], confidence, class_name))
        
        # Update tracker
        self.tracker.update_tracks(detections, frame=frame)
        
        tracks = []
        current_time = time.time()
        
        # Process confirmed tracks
        for track in self.tracker.tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            bbox = track.to_tlbr()  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, bbox)
            
            # Compute centroid
            centroid = ((x1 + x2) // 2, (y1 + y2) // 2)
            
            # Update track history
            if track_id not in self.track_history:
                self.track_history[track_id] = []
            self.track_history[track_id].append(centroid)
            
            # Keep only last 10 centroids
            if len(self.track_history[track_id]) > 10:
                self.track_history[track_id] = self.track_history[track_id][-10:]
            
            # Update first seen time
            if track_id not in self.track_first_seen:
                self.track_first_seen[track_id] = current_time
            
            # Compute dwell time
            dwell_seconds = current_time - self.track_first_seen[track_id]
            
            # Compute velocity
            history = self.track_history[track_id]
            if len(history) >= 2:
                dx = float(history[-1][0] - history[-2][0])
                dy = float(history[-1][1] - history[-2][1])
            else:
                dx = 0.0
                dy = 0.0
            
            # Find the corresponding detection to get confidence and class
            confidence = 0.0
            class_name = "unknown"
            for det_bbox, det_conf, det_class in detections:
                det_x1, det_y1, det_x2, det_y2 = det_bbox
                # Check if this detection matches the track
                if (abs(det_x1 - x1) < 10 and abs(det_y1 - y1) < 10 and 
                    abs(det_x2 - x2) < 10 and abs(det_y2 - y2) < 10):
                    confidence = det_conf
                    class_name = det_class
                    break
            
            track_obj = Track(
                track_id=track_id,
                class_name=class_name,
                confidence=confidence,
                bbox=[x1, y1, x2, y2],
                velocity=Velocity(dx=dx, dy=dy),
                dwell_seconds=dwell_seconds
            )
            tracks.append(track_obj)
        
        return tracks

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
                        # Decode JSON payload
                        payload = json.loads(message['data'])
                        frame_bytes_b64 = payload.get('frame_bytes')
                        
                        if not frame_bytes_b64:
                            continue
                            
                        # Decode base64 to bytes
                        frame_bytes = base64.b64decode(frame_bytes_b64)
                        
                        # Process frame
                        tracks = self._process_frame(frame_bytes)
                        
                        # Compute scene tags
                        current_hour = datetime.now().hour
                        scene_tags = self._compute_scene_tags(tracks, current_hour)
                        
                        # Build output
                        output = PerceptionOutput(
                            truck_id=self.truck_id,
                            frame_id=self.frame_id,
                            timestamp=datetime.now().isoformat(),
                            tracks=tracks,
                            scene_tags=scene_tags
                        )
                        
                        # Publish to output channel
                        await self.redis.publish(
                            self.output_channel,
                            output.model_dump_json()
                        )
                        
                        # Log processing info
                        self.logger.debug(
                            "Frame processed",
                            frame_id=self.frame_id,
                            track_count=len(tracks)
                        )
                        
                        self.frame_id += 1
                        
                except Exception as e:
                    self.logger.error("Error processing frame", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.input_channel)

    async def run_from_file(self, video_path: str):
        """Process video file directly for testing"""
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return
            
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            self.logger.error(f"Could not open video: {video_path}")
            return
        
        self.logger.info(f"Processing video: {video_path}")
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    self.logger.info("End of video reached")
                    break
                
                # Encode frame to JPEG bytes
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Process frame
                tracks = self._process_frame(frame_bytes)
                
                # Compute scene tags
                current_hour = datetime.now().hour
                scene_tags = self._compute_scene_tags(tracks, current_hour)
                
                # Build output
                output = PerceptionOutput(
                    truck_id=self.truck_id,
                    frame_id=self.frame_id,
                    timestamp=datetime.now().isoformat(),
                    tracks=tracks,
                    scene_tags=scene_tags
                )
                
                # Publish to output channel
                if self.redis:
                    await self.redis.publish(
                        self.output_channel,
                        output.model_dump_json()
                    )
                
                # Log processing info
                self.logger.debug(
                    "Frame processed",
                    frame_id=self.frame_id,
                    track_count=len(tracks)
                )
                
                self.frame_id += 1
                
                # Simulate 30 FPS
                await asyncio.sleep(1/30)
                
        except Exception as e:
            self.logger.error("Error processing video file", error=str(e))
        finally:
            cap.release()
            self.logger.info("Video processing completed")


if __name__ == "__main__":
    agent = PerceptionAgent()
    asyncio.run(agent.start())
    asyncio.run(agent.run_from_file("test_video.mp4"))