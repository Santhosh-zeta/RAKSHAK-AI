from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from pydantic import BaseModel

# --- 1. Define the Global State ---
class AgentState(TypedDict):
    trip_id: str
    vision_risk: float
    behavior_risk: float
    route_risk: float
    digital_twin_anomaly: bool
    digital_twin_risk: float
    fusion_score: float
    decision_action: str
    explanation: str

# --- 2. Define the Agent Nodes ---
def perception_agent_node(state: AgentState):
    """Placeholder for YOLOv8 Vision Integration"""
    # Logic to fetch latest camera frames or simulated detections
    return {"vision_risk": getattr(state, 'vision_risk', 0.0)}

def behavior_agent_node(state: AgentState):
    """Placeholder for Suspicious Behavior Tracking"""
    return {"behavior_risk": getattr(state, 'behavior_risk', 0.0)}

def route_agent_node(state: AgentState):
    """Placeholder for Geo-Spatial risk analysis"""
    return {"route_risk": getattr(state, 'route_risk', 0.0)}

def digital_twin_agent_node(state: AgentState):
    """Placeholder for Anomaly detection from Isolation Forest"""
    return {
        "digital_twin_anomaly": getattr(state, 'digital_twin_anomaly', False),
        "digital_twin_risk": getattr(state, 'digital_twin_risk', 0.0)
    }

def risk_fusion_agent_node(state: AgentState):
    """Core brain: Bayesian or Weighted Risk Compilation"""
    # Simply sum the risks for now as a mock fusion
    v_risk = state.get('vision_risk', 0.0)
    b_risk = state.get('behavior_risk', 0.0)
    r_risk = state.get('route_risk', 0.0)
    d_risk = state.get('digital_twin_risk', 0.0)
    
    total = min(100.0, v_risk + b_risk + r_risk + d_risk)
    
    return {"fusion_score": total}

def decision_agent_node(state: AgentState):
    """Evaluates risk severity and builds response policy"""
    score = state.get('fusion_score', 0.0)
    if score > 70:
        action = "High Alert - Stop Truck & Notify Police"
    elif score > 40:
        action = "Warning - Route Deviation Alert"
    else:
        action = "No Action"
        
    return {"decision_action": action}

def explainability_agent_node(state: AgentState):
    """Uses LLM to describe WHY the decision was made"""
    action = state.get('decision_action', "No Action")
    score = state.get('fusion_score', 0.0)
    
    if action == "No Action":
        desc = "Trip is progressing normally."
    else:
        desc = f"Escalated due to risk score {score}."
        
    return {"explanation": desc}

# --- 3. Build the LangGraph Workflow ---
def build_rakshak_orchestrator():
    builder = StateGraph(AgentState)
    
    # Add Nodes
    builder.add_node("perception", perception_agent_node)
    builder.add_node("behavior", behavior_agent_node)
    builder.add_node("route", route_agent_node)
    builder.add_node("digital_twin", digital_twin_agent_node)
    builder.add_node("risk_fusion", risk_fusion_agent_node)
    builder.add_node("decision", decision_agent_node)
    builder.add_node("explain", explainability_agent_node)
    
    # Add Edges (Linear Flow for mock)
    builder.set_entry_point("perception")
    builder.add_edge("perception", "behavior")
    builder.add_edge("behavior", "route")
    builder.add_edge("route", "digital_twin")
    builder.add_edge("digital_twin", "risk_fusion")
    builder.add_edge("risk_fusion", "decision")
    builder.add_edge("decision", "explain")
    builder.add_edge("explain", END)

    return builder.compile()

# Generate global instance
rakshak_workflow = build_rakshak_orchestrator()
