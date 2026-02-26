# RAKSHAK AI

RAKSHAK AI is an intelligent surveillance and telemetry platform designed for high-value fleet monitoring. It merges real-time GPS tracking, computer vision (YOLOv8), and multi-agent AI risk analysis to provide preemptive intelligence and operational command.

## Architecture

The system follows a decoupled client-server architecture.

```mermaid
graph TD
    subgraph Frontend [Next.js Web Application]
        UI[Command Center UI]
        LM[Live Monitoring]
        RA[Risk Analysis]
        AL[Alerts Hub]
    end

    subgraph Backend [Django REST Framework]
        API[API Gateway]
        DB[(PostgreSQL / SQLite)]
    end
    
    subgraph AI Core [Multi-Agent System]
        VA[Vision Agent - YOLOv8]
        BA[Behavior Agent]
        RFA[Risk Fusion Agent]
        EA[Explainability Agent - LLM]
    end

    UI --> |REST / JSON| API
    LM --> |REST / JSON| API
    RA --> |REST / JSON| API
    AL --> |REST / JSON| API
    
    API <--> DB
    API <--> VA
    API <--> BA
    API <--> RFA
    RFA <--> EA
```

## Setup & Installation

### 1. Backend Setup (Django + AI Core)

The backend drives the API endpoints, manages the database, and hosts the AI agents (LangGraph/YOLO).

**Prerequisites:** Python 3.10+, pip, and a virtual environment.

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply database migrations
python manage.py makemigrations
python manage.py migrate

# 5. Start the development server
python manage.py runserver
```

The server will initialize on `http://localhost:8000/`. Reference `backend/API_REFERENCE.md` for endpoint specifications.

### 2. Frontend Setup (Next.js)

The frontend is a high-performance Next.js application styled with Tailwind CSS and Framer Motion.

**Prerequisites:** Node.js 18.17+, npm.

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install NPM dependencies
npm install

# 3. Start the Turbopack development server
npm run dev
```

The application will initialize on `http://localhost:3000/`.

## Core Components
1. **Command Center Dashboard:** Real-time telemetry, spatial mapping, and aggregate risk metrics.
2. **Live Monitoring:** Dynamic camera feeds with integrated computer vision inferences for localized anomalies.
3. **Risk Analysis:** AI-driven reporting utilizing predictive Bayesian models for cargo and route evaluation.
4. **Alerts Intelligence Hub:** Priority-based alert feed with explainable AI analysis and recommended rapid responses.