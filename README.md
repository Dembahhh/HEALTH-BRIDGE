# HEALTH-BRIDGE AI

A preventive health coaching system for hypertension and type 2 diabetes risk assessment, designed for low-resource African settings.

**Live Demo:** [https://healthbridge-ai.netlify.app](https://healthbridge-ai.netlify.app) | [Firebase Hosting](https://healthbridge-ai-e96f5.firebaseapp.com)

## Overview

Health-Bridge AI combines a FastAPI backend with a React frontend, featuring a multi-agent architecture powered by CrewAI and RAG (Retrieval-Augmented Generation) using ChromaDB. The system provides personalized health guidance while considering social determinants of health (SDOH) constraints.

Key capabilities:
- **Multi-turn intake** with smart question generation and 3-layer field extraction (Semantic Matcher -> LLM -> Regex)
- **5 specialized AI agents** for risk assessment, constraints analysis, habit planning, and safety review
- **Parallel agent execution** for faster intake processing (Risk + SDOH run concurrently)
- **Corrective RAG** with query rewriting and a critic layer for guideline retrieval accuracy
- **Graph-style memory** with entity extraction, temporal pattern detection, and relationship tracking
- **Opik tracing** for observability across the full agent pipeline
- **Golden dataset evaluation** with 45 test cases across 3 tiers

## Architecture

```
+-----------------------------------------------------------------+
|                        FRONTEND (React)                          |
|  +----------+  +----------+  +----------+  +------------------+ |
|  |  Login   |  |Onboarding|  |   Chat   |  |    Dashboard     | |
|  +----------+  +----------+  +----------+  +------------------+ |
|                         | Firebase Auth |                        |
+-----------------------------------------------------------------+
                              | REST API |
+-----------------------------------------------------------------+
|                       BACKEND (FastAPI)                           |
|  +------------------------------------------------------------+ |
|  |               Session Manager (Orchestration)               | |
|  |  Conversation State | Input Collector | Pattern Detector    | |
|  +------------------------------------------------------------+ |
|  |               3-Layer Field Extraction                      | |
|  |  Semantic Matcher -> LLM (Gemini/OpenAI) -> Regex Fallback | |
|  +------------------------------------------------------------+ |
|  |                Multi-Agent System (CrewAI)                  | |
|  |  +-------+ +------+ +------+ +-------+ +--------+          | |
|  |  |Intake |>|Risk  |>| SDOH |>| Habit |>| Safety |          | |
|  |  |Agent  | |Agent | |Agent | | Coach | | Agent  |          | |
|  |  +-------+ +--+---+ +--+---+ +---+---+ +----+---+          | |
|  |                |        |         |          |              | |
|  |          (parallel when PARALLEL_CREW=true)                 | |
|  +------------------------------------------------------------+ |
|  |                    Tools & Services                         | |
|  |  +----------+  +-----------+  +----------+  +----------+   | |
|  |  |   RAG    |  | Semantic  |  |  Cognee  |  | Pattern  |   | |
|  |  |Retriever |  |  Memory   |  |  Memory  |  | Detector |   | |
|  |  +----+-----+  +-----+----+  +----+-----+  +----+-----+   | |
|  |       +---------------+-----------+              |          | |
|  |                   ChromaDB                       |          | |
|  +------------------------------------------------------------+ |
|  |                Observability (Opik)                          | |
|  |  Tracing | Tool spans | Session spans | CrewAI traces      | |
|  +------------------------------------------------------------+ |
|  |                     MongoDB                                 | |
|  |    Users | HealthProfiles | HabitPlans | ChatSessions       | |
|  +------------------------------------------------------------+ |
+-----------------------------------------------------------------+
```

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| CrewAI | Multi-agent orchestration |
| ChromaDB | Vector database for RAG & memory |
| MongoDB + Beanie | Document database with ODM |
| Firebase Admin | Authentication |
| SentenceTransformers | Text embeddings (all-MiniLM-L6-v2) |
| Gemini / OpenAI / GitHub Models | LLM providers |
| Opik | Tracing and observability |

### Frontend
| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| Vite | Build tool |
| TailwindCSS | Styling |
| Redux Toolkit | State management |
| Firebase | Authentication |
| Axios | HTTP client |

## Project Structure

```
HEALTH-BRIDGE/
├── .agent/                        # Agent configuration
├── .pre-commit-config.yaml        # Pre-commit hooks config
├── .secrets.baseline              # detect-secrets baseline
├── data/                          # Shared data directory
├── docker-compose.yml             # 3-service Docker Compose (MongoDB + Backend + Nginx)
├── netlify.toml                   # Netlify deployment config
├── nginx/                         # Nginx Dockerfile + config
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── agents.py          # 5 agent definitions
│   │   │   ├── crew.py            # Crew assembly + ParallelIntakeOrchestrator
│   │   │   ├── orchestrator.py    # Orchestration logic
│   │   │   ├── tasks.py           # Task definitions with Pydantic output
│   │   │   ├── models.py          # Profile, RiskAssessment, Constraints, HabitPlan, SafetyReview
│   │   │   └── tools.py           # 7 CrewAI tools with timeout/retry
│   │   ├── api/routes/            # REST API endpoints
│   │   ├── core/
│   │   │   ├── config.py          # Centralized Opik tracing config
│   │   │   ├── rag/
│   │   │   │   ├── retriever.py   # RAG retriever
│   │   │   │   ├── critic.py      # Corrective RAG critic
│   │   │   │   └── query_rewriter.py
│   │   │   └── memory/
│   │   │       ├── semantic_memory.py  # ChromaDB-backed memory
│   │   │       └── cognee_memory.py    # Graph-style memory with entity extraction
│   │   ├── models/                # MongoDB/Beanie models
│   │   └── services/
│   │       ├── session_manager.py     # Session orchestration
│   │       ├── conversation_state.py  # Multi-turn state tracking
│   │       ├── input_collector.py     # Readiness assessment
│   │       ├── llm_extractor.py       # 3-layer extraction
│   │       ├── semantic_matcher.py    # Semantic field matching
│   │       ├── question_generator.py  # Adaptive question generation
│   │       ├── pattern_detector.py    # Behavioral pattern detection
│   │       └── intervention_engine.py # Intervention recommendations
│   ├── tests/
│   │   ├── golden/                # Golden dataset (45 test cases)
│   │   ├── eval_runner.py         # Evaluation harness
│   │   └── test_golden.py         # Pytest integration
│   ├── data/guidelines/           # Medical guideline documents
│   ├── chat_cli.py                # CLI chat interface
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   ├── context/               # React context providers (ThemeContext)
│   │   ├── pages/                 # Route pages
│   │   ├── features/              # Redux slices
│   │   └── services/              # API & Firebase clients
│   └── package.json
└── package.json
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or Atlas)
- Firebase project (for authentication)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env with your Firebase config
```

## Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# Environment
DEBUG=true
ENV=development

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=healthbridge

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# LLM Provider (choose one)
GEMINI_API_KEY=your-gemini-api-key
# OPENAI_API_KEY=your-openai-key
# GITHUB_TOKEN=your-github-token

# LLM Settings
LLM_MODEL=gemini/gemini-1.5-flash
LLM_TEMPERATURE=0.3

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Agent Settings
AGENT_VERBOSE=false

# Parallel Execution (Phase 8)
PARALLEL_CREW=false       # Set true for concurrent Risk + SDOH

# Tracing (Phase 9)
TRACING_ENABLED=false     # Set true + provide OPIK_API_KEY
OPIK_API_KEY=
OPIK_PROJECT_NAME=healthbridge
OPIK_WORKSPACE=default

# Memory Backend (Phase 11)
MEMORY_BACKEND=semantic   # or "cognee" for graph-style memory

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Auth (dev only - NEVER use in production)
# SKIP_AUTH=true           # Uncomment ONLY for local development without Firebase
# ALLOW_DEV_TOKEN=false
# DEV_TOKEN=
```

### Frontend Environment Variables

Create `frontend/.env`:

```env
# Base URL of the backend — the frontend service layer appends /api/* paths
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abc123
```

## Running the Application

### Backend (API Server)

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

### Backend (CLI Chat)

```bash
cd backend

# Intake session (new user)
python chat_cli.py --intake

# Follow-up session (returning user)
python chat_cli.py --followup

# General health questions
python chat_cli.py --general

# With options
python chat_cli.py --intake --clear --user test_user --new-session
```

### Frontend

```bash
cd frontend
npm run dev
```

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Multi-Agent System

The system uses 5 specialized CrewAI agents:

| Agent | Role | Tools |
|-------|------|-------|
| **Intake Specialist** | Collects and structures health data | None |
| **Risk Researcher** | Estimates hypertension/diabetes risk bands | `Retrieve Guidelines`, `Recall User Memory` |
| **SDOH Analyst** | Identifies social/economic constraints | `Save User Constraint`, `Recall User Memory` |
| **Habit Coach** | Creates personalized 4-week plans | `Recall User Memory`, `Track Habit Progress` |
| **Safety Officer** | Validates all responses for safety | `Retrieve Guidelines` |

### Execution Modes

- **Sequential** (default): Intake -> Risk -> SDOH -> Plan -> Safety
- **Parallel** (`PARALLEL_CREW=true`): Intake -> (Risk || SDOH) -> Plan -> Safety

## 3-Layer Field Extraction

User input is processed through 3 extraction layers for robustness:

1. **Semantic Matcher** (free, fast) - Embedding similarity, synonym expansion, intent classification, fuzzy matching
2. **LLM Extractor** (API call) - Only for complex/ambiguous inputs the semantic matcher can't handle
3. **Regex Fallback** (always available) - Pattern-based extraction for common formats

This saves 80%+ of LLM API calls while maintaining accuracy.

## Memory System

### Semantic Memory (ChromaDB)
- User-specific vector storage with session isolation and TTL
- Memory types: profile, constraint, habit_plan, outcome, conversation
- Deduplication with cosine distance threshold (0.35)

### Cognee Memory (Graph-style)
- Regex-based entity extraction (conditions, demographics, lifestyle, family)
- Relationship tracking (family-condition, lifestyle-condition links)
- Temporal pattern detection (engagement gaps, adherence trends)
- Habit status tracking (started, active, struggling, stopped, resumed)

## Testing

### CLI Smoke Test
```bash
cd backend
python chat_cli.py --intake --clear --user test
```

### Golden Dataset (Tier 1 - no LLM needed)
```bash
cd backend
python -m pytest tests/test_golden.py::TestExtractionAccuracy -v
```

### Golden Dataset (Tier 2-3 - requires LLM)
```bash
cd backend
RUN_E2E_EVAL=true python -m pytest tests/test_golden.py -v
```

### Evaluation Harness
```bash
cd backend
python -m tests.eval_runner --tier 1   # Extraction accuracy
python -m tests.eval_runner --tier 2   # E2E intake (needs RUN_E2E_EVAL=true)
python -m tests.eval_runner --tier 3   # Safety boundary (needs RUN_E2E_EVAL=true)
```

## Safety Features

- No diagnostic claims (e.g., "You have diabetes")
- No dosage or medication advice
- Red flag escalation for dangerous symptoms (chest pain, breathing difficulty, etc.)
- SDOH-aware recommendations (affordable, accessible)
- Final safety review by Safety Agent on every response
- Prompt injection detection in safety test cases

## API Endpoints

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/session` | Create new chat session |
| POST | `/api/chat/message` | Send message & get AI response |
| POST | `/api/chat/stream` | SSE streaming response (auto-routes quick/full) |
| POST | `/api/chat/quick` | Quick single-turn response (lighter pipeline) |
| POST | `/api/chat/auto` | Auto-routed message (picks quick or full based on complexity) |
| POST | `/api/chat/feedback` | Submit feedback on an assistant message |
| GET | `/api/chat/session/{session_id}/messages` | Get conversation history for a session |
| GET | `/api/chat/sessions` | List all chat sessions for current user |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get user health profile |
| PUT | `/api/profile` | Update profile |
| GET | `/api/profile/risk` | Get risk assessment |

### Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plans/current` | Get active habit plan |
| GET | `/api/plans/history` | Get plan history |
| POST | `/api/plans/feedback` | Submit adherence feedback |

## SSE Streaming

The `/api/chat/stream` endpoint uses **Server-Sent Events** for real-time responses. It auto-routes between two pipelines:

| Pipeline | Trigger | Latency |
|----------|---------|---------|
| **Quick** | Simple factual questions | 2–5 seconds |
| **Full Crew** | Complex health assessments | 20–60 seconds |

SSE event types: `start`, `progress`, `complete`, `error`, plus a `[DONE]` sentinel to signal end of stream.

## Rate Limiting

All API endpoints have per-user rate limits:

| Endpoint group | Limit |
|----------------|-------|
| Chat session creation | 10 / minute |
| Full message (`/message`) | 20 / minute |
| Quick message (`/quick`) | 30 / minute |
| Streaming (`/stream`) | 10 / minute |
| Feedback (`/feedback`) | 20 / minute |
| Session list / history | 30 / minute |

## Docker

A `docker-compose.yml` is provided to run the full stack locally with three services: **MongoDB**, the **FastAPI backend**, and **Nginx** (serves the compiled frontend and reverse-proxies `/api` to the backend).

```bash
# Build all images and start services
docker-compose up --build
```

The app will be available at `http://localhost` (port 80). Nginx handles routing:
- Static frontend files served directly
- `/api/*` requests proxied to the FastAPI backend

## Deployment

### Production Architecture

```
Browser → Firebase Hosting (static SPA) → Render Web Service (FastAPI)
       or
Browser → Netlify (static SPA + /api proxy) → Render Web Service (FastAPI)
```

- **Frontend:** Firebase Hosting — `https://healthbridge-ai-e96f5.firebaseapp.com` / `https://healthbridge-ai-e96f5.web.app`
- **Frontend (alt):** Netlify — `https://healthbridge-ai.netlify.app`
- **Backend:** Render Web Service — `https://health-bridge-x2ev.onrender.com`

> **Note:** Render's free tier spins down after inactivity. Expect a ~50-second cold-start delay on the first request after a period of no traffic.

### Key Production Environment Variables

```env
# Backend — CORS must include the production frontend domain(s)
CORS_ORIGINS=https://healthbridge-ai-e96f5.firebaseapp.com,https://healthbridge-ai-e96f5.web.app,https://healthbridge-ai.netlify.app

# Set production mode
ENV=production
DEBUG=false
```

## Authentication

The app uses **Firebase Authentication** with two sign-in methods:

- **Google OAuth** (popup-based)
- **Email / password** registration and login

After sign-in, the Firebase ID token is sent as a `Bearer` token in the `Authorization` header of every API request. The backend validates the token using Firebase Admin SDK.

## Theming & UI

The frontend supports:

- **Dark / light mode** toggle (`ThemeToggle` component)
- **Accent color system** — orange and purple themes
- Theme state is managed via `ThemeContext` provider

## Onboarding Flow

First-time users complete a multi-step onboarding wizard (`OnboardingPage.jsx`):

1. **Intro / Welcome**
2. **Demographics** — age, biological sex
3. **Family History** — hereditary conditions
4. **Lifestyle** — smoking, alcohol consumption
5. **Activity Level** — exercise habits

## Pre-commit Hooks & Security

The repo uses pre-commit hooks for code quality and secret detection:

```bash
pip install pre-commit
pre-commit install
```

- **`.pre-commit-config.yaml`** — code style and lint hooks
- **`.secrets.baseline`** — `detect-secrets` baseline to prevent accidental secret commits

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Install pre-commit hooks: `pre-commit install`
4. Make your changes and add tests where appropriate
5. Run the test suite: `cd backend && python -m pytest tests/`
6. Push your branch and open a pull request

Please follow the existing code style and include tests for new functionality.

## License

MIT License
