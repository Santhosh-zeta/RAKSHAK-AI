"""
RAKSHAK AI - Explainability Agent
Generates LLM-powered natural language explanations for security alerts.
Supports OpenAI GPT-4o-mini, Ollama (local), and rule-based template fallback.
Publishes ExplanationOutput to rakshak.explain.output
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import httpx
import redis.asyncio as aioredis
from pydantic import BaseModel
import structlog


class ExplanationOutput(BaseModel):
    incident_id: str
    truck_id: str
    timestamp: str
    explanation_text: str
    llm_model_used: str
    generation_time_ms: float
    confidence_noted: float
    risk_level: str


class ExplainabilityAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.decision_channel = "rakshak.decision.output"
        self.risk_channel = "rakshak.risk.output"
        self.output_channel = "rakshak.explain.output"
        self.llm_provider = os.getenv("LLM_PROVIDER", "template")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        self.redis = None
        self.running = False
        self._risk_cache: dict = {}    # incident_id -> risk payload
        self.logger = structlog.get_logger().bind(agent="explainability_agent")

    async def start(self):
        """Initialize the explainability agent"""
        # Connect to Redis
        self.redis = aioredis.from_url(self.redis_url)
        
        self.running = True
        self.logger.info(f"Explainability agent started with provider: {self.llm_provider}")

    async def stop(self):
        """Stop the explainability agent"""
        self.running = False
        if self.redis:
            await self.redis.close()
        self.logger.info("Explainability agent stopped")

    def _build_prompt(self, decision_payload: dict, risk_payload: dict) -> str:
        """Build prompt for LLM"""
        # Extract fields from both payloads
        truck_id = risk_payload.get('truck_id', decision_payload.get('truck_id', 'UNKNOWN'))
        timestamp = datetime.now().isoformat()
        risk_level = risk_payload.get('risk_level', decision_payload.get('risk_level', 'UNKNOWN'))
        score = risk_payload.get('composite_risk_score', 0.0)
        confidence = risk_payload.get('confidence', 0.0)
        rule_name = decision_payload.get('rule_name', 'NO_RULE')
        fusion_method = risk_payload.get('fusion_method', 'UNKNOWN')
        behaviour_score = risk_payload.get('component_scores', {}).get('behaviour', 0.0)
        twin_score = risk_payload.get('component_scores', {}).get('twin', 0.0)
        route_score = risk_payload.get('component_scores', {}).get('route', 0.0)
        triggered_rules = risk_payload.get('triggered_rules', [])
        actions_taken = decision_payload.get('actions_taken', [])

        return f"""You are RAKSHAK AI, an intelligent cargo security analyst.
Analyze the following security alert and write a clear, concise 3-4 sentence
explanation of why this cargo truck is flagged as {risk_level} risk.
Be specific about time, location evidence, and behavioral signals observed.
Do NOT speculate. Only describe what the sensor data shows.

ALERT DETAILS:
- Truck ID: {truck_id}
- Time: {timestamp}
- Risk Level: {risk_level}
- Composite Risk Score: {score:.2f} (Confidence: {confidence:.0%})
- Rule Triggered: {rule_name}
- Fusion Method: {fusion_method}

SENSOR EVIDENCE:
- Behaviour Anomaly Score: {behaviour_score:.2f}
- Twin Deviation Score: {twin_score:.2f}
- Route Risk Score: {route_score:.2f}
- Triggered Flags: {", ".join(triggered_rules)}
- Actions Taken: {", ".join(actions_taken)}

Write the security alert explanation:"""

    async def _call_openai(self, prompt: str) -> tuple[str, str]:
        """Call OpenAI API for explanation"""
        import openai  # Import inside function to handle ImportError gracefully
        client = openai.AsyncOpenAI(api_key=self.openai_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini", max_tokens=300,
            messages=[{"role": "system", "content": "You are a cargo security AI."},
                      {"role": "user", "content": prompt}])
        return response.choices[0].message.content, "gpt-4o-mini"

    async def _call_ollama(self, prompt: str) -> tuple[str, str]:
        """Call Ollama API for explanation"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_host}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False})
            data = response.json()
            return data["response"], self.ollama_model

    def _template_explanation(self, decision_payload: dict, risk_payload: dict) -> tuple[str, str]:
        """Generate rule-based explanation string using f-string template"""
        truck_id = risk_payload.get('truck_id', decision_payload.get('truck_id', 'UNKNOWN'))
        timestamp = datetime.now().isoformat()
        risk_level = risk_payload.get('risk_level', decision_payload.get('risk_level', 'UNKNOWN'))
        score = risk_payload.get('composite_risk_score', 0.0)
        triggered_rules = risk_payload.get('triggered_rules', [])
        actions_taken = decision_payload.get('actions_taken', [])
        
        # Take top 2 triggered flags
        top_flags = ", ".join(triggered_rules[:2]) if triggered_rules else "None"
        
        explanation_text = f"""Security alert generated for truck {truck_id} at {timestamp}. 
The system has classified this as {risk_level} risk with a composite score of {score:.2f}. 
Sensor data indicates: {top_flags}. 
Actions taken: {', '.join(actions_taken) if actions_taken else 'None'}. 
This alert reflects potential security concerns based on real-time monitoring of truck behavior, location, and environmental factors."""
        
        return explanation_text, "rule_based_template"

    async def _generate_explanation(self, decision_payload: dict, risk_payload: dict) -> tuple[str, str]:
        """Generate explanation using configured LLM provider"""
        prompt = self._build_prompt(decision_payload, risk_payload)
        try:
            if self.llm_provider == "openai" and self.openai_key:
                return await self._call_openai(prompt)
            elif self.llm_provider == "ollama":
                return await self._call_ollama(prompt)
            else:
                return self._template_explanation(decision_payload, risk_payload)
        except Exception as e:
            self.logger.warning(f"LLM call failed: {e}, falling back to template")
            return self._template_explanation(decision_payload, risk_payload)

    async def _handle_decision(self, decision_payload: dict):
        """Handle decision payload to generate explanation"""
        # Only process if rule_id is not None (a rule actually fired)
        rule_id = decision_payload.get('rule_id')
        if rule_id is None:
            return  # No rule fired, no explanation needed
        
        incident_id = decision_payload.get('incident_id', str(uuid.uuid4()))
        truck_id = decision_payload.get('truck_id', 'UNKNOWN')
        
        # Get cached risk_payload
        risk_payload = self._risk_cache.get(incident_id, {})
        
        start_time = asyncio.get_event_loop().time()
        explanation_text, model_used = await self._generate_explanation(decision_payload, risk_payload)
        gen_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Get risk level and confidence from payloads
        risk_level = risk_payload.get('risk_level', decision_payload.get('risk_level', 'UNKNOWN'))
        confidence = risk_payload.get('confidence', 0.0)
        
        # Build ExplanationOutput
        explanation_output = ExplanationOutput(
            incident_id=incident_id,
            truck_id=truck_id,
            timestamp=datetime.now().isoformat(),
            explanation_text=explanation_text,
            llm_model_used=model_used,
            generation_time_ms=gen_time_ms,
            confidence_noted=confidence,
            risk_level=risk_level
        )
        
        # Store in Redis: explanation:{incident_id} = JSON, TTL 86400s
        explanation_key = f"explanation:{incident_id}"
        await self.redis.setex(explanation_key, 86400, explanation_output.model_dump_json())
        
        # Publish to output channel
        await self.redis.publish(
            self.output_channel,
            explanation_output.model_dump_json()
        )
        
        # Log info with incident_id, model_used, gen_time_ms
        self.logger.info(
            "Explanation generated",
            incident_id=incident_id,
            model_used=model_used,
            generation_time_ms=round(gen_time_ms, 2)
        )

    async def run(self):
        """Main processing loop listening to Redis channels"""
        if not self.running or not self.redis:
            self.logger.error("Agent not started or Redis not connected")
            return
        
        try:
            # Subscribe to BOTH rakshak.decision.output AND rakshak.risk.output
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(self.decision_channel, self.risk_channel)
            
            self.logger.info(f"Subscribed to {self.decision_channel} and {self.risk_channel}")
            
            # Processing loop
            while self.running:
                try:
                    # Wait for message
                    message = await pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        channel = message['channel'].decode('utf-8')
                        payload = json.loads(message['data'])
                        
                        if channel == self.risk_channel:
                            # Cache payload by incident_id in self._risk_cache
                            incident_id = payload.get('incident_id')
                            if incident_id:
                                self._risk_cache[incident_id] = payload
                                # Trim cache to last 100 entries
                                if len(self._risk_cache) > 100:
                                    # Remove oldest entries (first 10%)
                                    keys_to_remove = list(self._risk_cache.keys())[:10]
                                    for key in keys_to_remove:
                                        self._risk_cache.pop(key, None)
                        
                        elif channel == self.decision_channel:
                            # Fire-and-forget: asyncio.create_task(self._handle_decision(payload))
                            asyncio.create_task(self._handle_decision(payload))
                        
                except Exception as e:
                    self.logger.error("Error processing message", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await pubsub.unsubscribe(self.decision_channel, self.risk_channel)


if __name__ == "__main__":
    agent = ExplainabilityAgent()
    
    async def main():
        await agent.start()
        await agent.run()
    
    asyncio.run(main())