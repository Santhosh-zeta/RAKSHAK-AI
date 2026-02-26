# RAKSHAK Backend <-> AI Integration Contract

This document explicitly defines the expected methods and input/output structures for the `.pkl` files or API endpoints being developed by the AI team.

---

## 1. Vision AI Agent (Perception)
*File mapping expected in:* `backend/surveillance/agents/perception_agent.py`

When the backend receives a Vision Event from the frontend cameras, it will pass the raw data payload to your inference wrapper.

**Expected Interface:**
```python
def process_vision_frame(frame_data_or_url: str) -> dict:
    """
    Input: Path to frame or base64 image data.
    Returns: Dictionary matching the format below.
    """
    return {
        "event_detected": "Person Detected", # None if normal
        "confidence": 0.92,
        "raw_risk_penalty": 25.0, # 0 to 100 scale on severity
        "details": "Person detected lingering near rear doors."
    }
```

---

## 2. Digital Twin & Behavior Agent
*File mapping expected in:* `backend/surveillance/agents/behavior_agent.py`

Every ping to `api/gps-logs/` (typically every 5-10 seconds for active trips) will pipe the latest telemetry to your isolation forest / threshold models.

**Expected Interface:**
```python
def evaluate_trip_behavior(truck_id: str, current_log: dict, historical_logs: list[dict]) -> dict:
    """
    Input:
      truck_id: UUID string format.
      current_log: { "speed_kmh": 60, "engine_status": True, ... }
      historical_logs: List of previous dicts to calculate anomaly deltas.
    Returns: Dictionary of behavior state.
    """
    return {
        "is_anomaly": True,
        "anomaly_type": "Abnormal Stop", # Engine running, speed 0 for > 15m
        "risk_penalty": 35.0
    }
```

---

## 3. Risk Fusion Agent (The Bayesian Core)
*File mapping expected in:* `backend/surveillance/agents/risk_fusion_agent.py`

Once all other agents return their `risk_penalty` scores, the backend Orchestrator script will pass them to your core fusion brain.

**Expected Interface:**
```python
def compute_unified_risk(baseline_route_risk: float, agent_penalties: dict) -> float:
    """
    Input:
      baseline_route_risk: 0.0 - 100.0 (Pre-calculated by GeoSpatialService)
      agent_penalties: {
         "vision": 25.0,
         "behavior": 35.0,
         "iot": 0.0
      }
    Returns: A single float representing the absolute current risk. (e.g., 78.5)
             The backend will natively handle Decision Policy actions if this > 70.
    """
    pass
```

---

## Process for handoff:
1. Save your Scikit-Learn / PyTorch models to the `backend/surveillance/ai_models/` directory.
2. In the `surveillance/agents/` files, build wrapper classes that load your `.pkl` files at initialization, and expose the methods above to receive the Django API calls.
