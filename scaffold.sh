#!/bin/bash
cd /home/ashwin/Documents/GitHub/RAKSHAK-AI/
mkdir -p backend
cd backend

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install django djangorestframework psycopg2-binary ultralytics opencv-python torch pandas numpy scikit-learn pydantic langgraph

# Start Django project
django-admin startproject rakshak .
python manage.py startapp surveillance

# Create the specified folder structure
mkdir -p surveillance/agents surveillance/ai_models surveillance/services surveillance/utils train_models

touch requirements.txt .env

# Create empty module __init__.py files
touch surveillance/agents/__init__.py surveillance/services/__init__.py surveillance/utils/__init__.py train_models/__init__.py

# Agents
touch surveillance/agents/perception_agent.py surveillance/agents/behavior_agent.py \
      surveillance/agents/route_agent.py surveillance/agents/digital_twin_agent.py \
      surveillance/agents/risk_fusion_agent.py surveillance/agents/decision_agent.py \
      surveillance/agents/explainability_agent.py surveillance/agents/orchestrator.py

# AI Models
touch surveillance/ai_models/behavior_model.pkl surveillance/ai_models/route_model.pkl surveillance/ai_models/risk_model.pkl

# Services
touch surveillance/services/sms_service.py surveillance/services/map_service.py \
      surveillance/services/llm_service.py surveillance/services/supabase_service.py

# Utils
touch surveillance/utils/feature_builder.py surveillance/utils/constants.py

# Train models
touch train_models/train_behavior.py train_models/train_route.py train_models/train_risk.py

# Create frontend folder structure as well
cd /home/ashwin/Documents/GitHub/RAKSHAK-AI/
mkdir -p frontend

echo "Scaffolding Complete"
