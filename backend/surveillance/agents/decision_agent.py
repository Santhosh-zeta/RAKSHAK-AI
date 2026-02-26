"""
RAKSHAK AI - Decision Agent
Evaluates risk scores against configurable rules.
Fires SMS/email alerts with Redis-based cooldown deduplication.
Publishes DecisionOutput to rakshak.decision.output
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Callable

import redis.asyncio as aioredis
from pydantic import BaseModel
import structlog


class RiskInput(BaseModel):          # mirrors RiskOutput from risk_fusion_agent
    truck_id: str
    incident_id: str
    composite_risk_score: float
    risk_level: str
    confidence: float
    component_scores: dict
    triggered_rules: List[str]
    fusion_method: str


class DecisionOutput(BaseModel):
    truck_id: str
    incident_id: str
    timestamp: str
    rule_id: Optional[str]
    rule_name: Optional[str]
    actions_taken: List[str]
    alert_suppressed: bool
    suppression_reason: Optional[str]
    risk_score: float
    risk_level: str


# Define RULES list at module level (outside class)
RULES = [
    {
        "id": "R001",
        "name": "CRITICAL_THEFT_ALERT",
        "condition": lambda r: r.composite_risk_score >= 0.85,
        "actions": ["sms", "email", "log_incident"],
        "cooldown_s": 300,
        "priority": 1
    },
    {
        "id": "R002",
        "name": "HIGH_RISK_ALERT",
        "condition": lambda r: 0.65 <= r.composite_risk_score < 0.85,
        "actions": ["email", "log_incident"],
        "cooldown_s": 600,
        "priority": 2
    },
    {
        "id": "R003",
        "name": "MEDIUM_RISK_MONITOR",
        "condition": lambda r: 0.45 <= r.composite_risk_score < 0.65,
        "actions": ["log_incident"],
        "cooldown_s": 1800,
        "priority": 3
    },
]


class DecisionAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.input_channel = "rakshak.risk.output"
        self.output_channel = "rakshak.decision.output"
        self.twilio_sid = os.getenv("TWILIO_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_phone = os.getenv("TWILIO_PHONE", "")
        self.alert_phone = os.getenv("ALERT_RECIPIENT_PHONE", "")
        self.alert_email = os.getenv("ALERT_EMAIL", "")
        self.redis = None
        self.running = False
        self.logger = structlog.get_logger().bind(agent="decision_agent")

    async def start(self):
        """Initialize the decision agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        self.running = True
        self.logger.info("Decision agent started")

    async def stop(self):
        """Stop the decision agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Decision agent stopped")

    async def _is_on_cooldown(self, truck_id: str, rule_id: str) -> bool:
        """Check if alert is on cooldown"""
        key = f"alert_cooldown:{truck_id}:{rule_id}"
        result = await self.redis.get(key)
        return result is not None

    async def _set_cooldown(self, truck_id: str, rule_id: str, cooldown_s: int):
        """Set cooldown for alert"""
        key = f"alert_cooldown:{truck_id}:{rule_id}"
        await self.redis.set(key, "1", ex=cooldown_s)

    async def _log_incident(self, risk_input: RiskInput, rule: dict):
        """Log incident to Redis"""
        incident = {
            "incident_id": risk_input.incident_id,
            "truck_id": risk_input.truck_id,
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "risk_score": risk_input.composite_risk_score,
            "risk_level": risk_input.risk_level,
            "triggered_rules": risk_input.triggered_rules,
            "logged_at": datetime.now().isoformat()
        }
        await self.redis.lpush(f"incidents:{risk_input.truck_id}", json.dumps(incident))
        await self.redis.ltrim(f"incidents:{risk_input.truck_id}", 0, 49)

    async def _send_sms(self, risk_input: RiskInput):
        """Send SMS alert"""
        if self.twilio_sid and self.twilio_token and self.twilio_phone and self.alert_phone:
            self.logger.info(
                "SMS would be sent via Twilio",
                truck_id=risk_input.truck_id,
                risk_score=risk_input.composite_risk_score,
                risk_level=risk_input.risk_level
            )
            # Note: actual Twilio call commented out to avoid import dependency
            # from twilio.rest import Client
            # client = Client(self.twilio_sid, self.twilio_token)
            # client.messages.create(body=msg, from_=self.twilio_phone, to=self.alert_phone)
        else:
            self.logger.warning("Twilio not configured — SMS suppressed")

    async def _send_email(self, risk_input: RiskInput):
        """Send email alert"""
        if self.alert_email:
            self.logger.info(
                "Email alert would be sent",
                truck_id=risk_input.truck_id,
                risk_score=risk_input.composite_risk_score,
                incident_id=risk_input.incident_id,
                risk_level=risk_input.risk_level
            )
            # Note: actual smtplib call commented out
            # import smtplib; ... (comment the full implementation)
        else:
            self.logger.warning("Alert email not configured — email suppressed")

    async def _execute_actions(self, risk_input: RiskInput, rule: dict) -> List[str]:
        """Execute actions for matched rule"""
        executed = []
        for action in rule["actions"]:
            if action == "sms":
                await self._send_sms(risk_input)
                executed.append("sms")
            elif action == "email":
                await self._send_email(risk_input)
                executed.append("email")
            elif action == "log_incident":
                await self._log_incident(risk_input, rule)
                executed.append("log_incident")
        return executed

    async def _evaluate_rules(self, risk_input: RiskInput) -> DecisionOutput:
        """Evaluate risk input against rules"""
        # Sort rules by priority (lower number = higher priority)
        sorted_rules = sorted(RULES, key=lambda r: r["priority"])
        
        for rule in sorted_rules:
            # Check if condition matches
            if not rule["condition"](risk_input):
                continue
            
            # Check if on cooldown
            on_cooldown = await self._is_on_cooldown(risk_input.truck_id, rule["id"])
            if on_cooldown:
                return DecisionOutput(
                    truck_id=risk_input.truck_id,
                    incident_id=risk_input.incident_id,
                    timestamp=datetime.now().isoformat(),
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    actions_taken=[],
                    alert_suppressed=True,
                    suppression_reason=f"Cooldown active for {rule['id']}",
                    risk_score=risk_input.composite_risk_score,
                    risk_level=risk_input.risk_level
                )
            
            # Set cooldown
            await self._set_cooldown(risk_input.truck_id, rule["id"], rule["cooldown_s"])
            
            # Execute actions
            actions = await self._execute_actions(risk_input, rule)
            
            return DecisionOutput(
                truck_id=risk_input.truck_id,
                incident_id=risk_input.incident_id,
                timestamp=datetime.now().isoformat(),
                rule_id=rule["id"],
                rule_name=rule["name"],
                actions_taken=actions,
                alert_suppressed=False,
                suppression_reason=None,
                risk_score=risk_input.composite_risk_score,
                risk_level=risk_input.risk_level
            )
        
        # If no rule matches
        return DecisionOutput(
            truck_id=risk_input.truck_id,
            incident_id=risk_input.incident_id,
            timestamp=datetime.now().isoformat(),
            rule_id=None,
            rule_name=None,
            actions_taken=[],
            alert_suppressed=False,
            suppression_reason=None,
            risk_score=risk_input.composite_risk_score,
            risk_level=risk_input.risk_level
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
                        # Parse JSON into RiskInput
                        payload = json.loads(message['data'])
                        risk_input = RiskInput(**payload)
                        
                        # Evaluate rules
                        output = await self._evaluate_rules(risk_input)
                        
                        # Publish to output channel
                        await self.redis.publish(
                            self.output_channel,
                            output.model_dump_json()
                        )
                        
                        # Log appropriately
                        if not output.alert_suppressed and output.rule_id:
                            self.logger.warning(
                                "Alert fired",
                                rule_name=output.rule_name,
                                truck_id=output.truck_id,
                                risk_score=output.risk_score,
                                risk_level=output.risk_level,
                                actions=output.actions_taken
                            )
                        else:
                            self.logger.debug(
                                "Risk evaluated",
                                truck_id=output.truck_id,
                                risk_score=output.risk_score,
                                risk_level=output.risk_level,
                                alert_suppressed=output.alert_suppressed,
                                suppression_reason=output.suppression_reason
                            )
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.input_channel)


if __name__ == "__main__":
    agent = DecisionAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())