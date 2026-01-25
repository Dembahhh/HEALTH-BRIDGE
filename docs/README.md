# HEALTH-BRIDGE AI

A preventive health coaching system for hypertension and type 2 diabetes risk assessment, designed for low-resource African settings.

## Overview

Health-Bridge AI combines a FastAPI backend with a React frontend, featuring a multi-agent architecture powered by CrewAI and RAG (Retrieval-Augmented Generation) using ChromaDB. The system provides personalized health guidance while considering social determinants of health (SDOH) constraints.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│
│  │  Login   │  │Onboarding│  │   Chat   │  │    Dashboard     ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘│
│                         ↓ Firebase Auth ↓                       │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API │
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Multi-Agent System (CrewAI)             │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐│ │
│  │  │ Intake  │→│  Risk   │→│  SDOH   │→│  Habit  │→│Safety ││ │
│  │  │ Agent   │ │ Agent   │ │ Agent   │ │  Coach  │ │Agent  ││ │
│  │  └─────────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬───┘│ │
│  └───────────────────┼──────────┼──────────┼──────────┼─────┘ │
│                      ↓          ↓          ↓          ↓       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Tools & Services                       │ │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────────────┐  │ │
│  │  │    RAG     │  │  Semantic   │  │     Guidelines    │  │ │
│  │  │ Retriever  │  │   Memory    │  │      Corpus       │  │ │
│  │  └──────┬─────┘  └──────┬──────┘  └─────────┬─────────┘  │ │
│  │         └───────────────┴───────────────────┘            │ │
│  │                      ChromaDB                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              ↓                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                     MongoDB                               │ │
│  │    Users │ HealthProfiles │ HabitPlans │ ChatSessions    │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
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
| SentenceTransformers | Text embeddings |
| Gemini API | LLM provider |

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
│   │   ├── agents/          # CrewAI agents & tools
│   │   ├── api/routes/      # REST API endpoints
│   │   ├── config/          # Settings & database
│   │   ├── core/
│   │   │   ├── rag/         # RAG pipeline (retriever, chunker, etc.)
│   │   │   └── memory/      # Semantic memory system
│   │   ├── models/          # MongoDB/Beanie models
│   │   └── services/        # Business logic
│   ├── data/guidelines/     # Medical guideline documents
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages
│   │   ├── features/        # Redux slices
│   │   └── services/        # API & Firebase clients
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
# Navigate to backend
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
# Navigate to frontend
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

# LLM (Gemini)
GEMINI_API_KEY=your-gemini-api-key
LLM_MODEL=gemini/gemini-1.5-flash
LLM_TEMPERATURE=0.7

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Redis (for background tasks)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Auth (dev only)
SKIP_AUTH=true
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

### Start Backend

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend

```bash
cd frontend

# Run Vite dev server
npm run dev
```

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

## Multi-Agent System

The system uses 5 specialized CrewAI agents:

| Agent | Role | Tools |
|-------|------|-------|
| **Intake Specialist** | Collects health data | None |
| **Risk Researcher** | Estimates risk bands | `retrieve_guidelines` |
| **SDOH Analyst** | Identifies constraints | `save_constraint`, `recall_memory` |
| **Habit Coach** | Creates 4-week plans | `recall_memory` |
| **Safety Officer** | Validates responses | `retrieve_guidelines` |

## Testing

### Integration Test

```bash
cd backend
python test_integration.py
```

### Agent Verification

```bash
cd backend
python verify_agents.py
```

## Data Flow

1. **User Authentication** - Firebase login - Protected routes
2. **Health Onboarding** - Profile form - Store in MongoDB
3. **Chat Interaction** - Send message - CrewAI processes
4. **RAG Retrieval** - ChromaDB vector search - Guidelines
5. **Agent Processing** - Sequential tasks - Safe response
6. **Memory Integration** - Recall past context - Personalization
7. **Plan Generation** - Habit plan - MongoDB storage

## Safety Features

- No diagnostic claims (e.g., "You have diabetes")
- No dosage or medication advice
- Red flag escalation for dangerous symptoms
- SDOH-aware recommendations (affordable, accessible)
- Final safety review by Safety Agent

## Key Design Decisions

### Multi-Agent Architecture
- CrewAI for agent orchestration with 5 specialized agents
- Sequential processing ensures data flows correctly between agents

### RAG Design
- ChromaDB for vector storage
- Curated WHO + MoH guideline corpus
- Query rewriting for better retrieval
- Corrective RAG critic for accuracy

### Semantic Memory
- User-specific memories in ChromaDB
- Types: Profile, Constraints, Habit Plans, Outcomes
- Enables personalized follow-up sessions

## License

MIT License
