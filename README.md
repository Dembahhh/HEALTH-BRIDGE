# HEALTH-BRIDGE AI

A preventive health coaching system for hypertension and type 2 diabetes risk assessment, designed for low-resource African settings.

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
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── agents.py          # 5 agent definitions
│   │   │   ├── crew.py            # Crew assembly + ParallelIntakeOrchestrator
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
│   │   ├── pages/                 # Route pages
│   │   ├── features/              # Redux slices
│   │   └── services/              # API & Firebase clients
│   └── package.json
└── docs/
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
VITE_API_URL=http://localhost:8000/api
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

## Alternative: Docker Deployment (Optional)

If you prefer using Docker instead of the manual setup above, you can run the entire stack with Docker Compose.

### Prerequisites for Docker
- Docker and Docker Compose installed
- `.env` files configured (see Configuration section above)

### Quick Start with Docker

```bash
# 1. Ensure environment files are configured
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit both .env files with your API keys and Firebase config

# 2. Start all services (backend, frontend, MongoDB, Redis)
docker-compose up --build

# 3. Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Docker Commands

Run in the background:
```bash
docker-compose up --build -d
```

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

Stop and remove all data (including database volumes):
```bash
docker-compose down -v
```

### What's Included in Docker Setup
- **Backend**: Python/FastAPI with CPU-optimized PyTorch (~1.8GB smaller)
- **Frontend**: React app served by nginx with API proxying
- **MongoDB 7**: Database with health checks and persistent storage
- **Redis 7**: Caching layer with health checks
- **ChromaDB**: Vector storage (persistent mode)

**Note**: The Docker setup uses optimized images and includes all dependencies. Database data persists in Docker volumes across container restarts.

## Production Deployment

### ChromaDB Setup for Multi-Worker Deployment

The application uses ChromaDB for vector storage. In development mode, it uses a persistent local file store. For production deployment with multiple FastAPI workers (to handle concurrent requests), you must use ChromaDB in HTTP mode with a standalone ChromaDB server to avoid database locking issues.

#### Option 1: Development Mode (Single Worker)
For local development or testing:

```bash
cd backend
# Ensure CHROMA_MODE=persistent in .env (default)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Production Mode (Multiple Workers)

1. **Start ChromaDB service:**
```bash
cd backend
docker-compose -f docker-compose.chromadb.yml up -d
```

2. **Set environment variables in `.env`:**
```env
CHROMA_MODE=http
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_AUTH_TOKEN=your-secure-token-here  # Optional but recommended
```

3. **Run FastAPI with multiple workers:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

Note: ChromaDB runs on port 8000 by default, so FastAPI should use a different port (e.g., 8001) in this setup.

4. **Verify ChromaDB connectivity:**
```bash
curl http://localhost:8001/health/chromadb
```

#### Health Check Endpoints
- `/health` - General API health status
- `/health/chromadb` - ChromaDB connectivity and document count

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
| GET | `/api/chat/history/{session_id}` | Get conversation history |

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
| POST | `/api/plans/feedback` | Submit adherence feedback |

## License

MIT License
