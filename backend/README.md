# Backend - Health-bridge AI

FastAPI backend for the Health-bridge AI preventive health coach.

## Directory Structure

```
backend/
├── app/
│   ├── api/          # API endpoints
│   │   └── routes/   # Route handlers (chat, profile, plans)
│   ├── core/
│   │   ├── rag/      # Embeddings, chunking, retrieval
│   │   ├── memory/   # Semantic memory manager
│   │   └── llm/      # LLM client wrappers
│   ├── agents/       # CrewAI agent definitions
│   │   ├── agents.py
│   │   ├── crew.py
│   │   ├── orchestrator.py   # Orchestration logic
│   │   ├── tasks.py
│   │   ├── models.py
│   │   └── tools.py          # Agent tools (file, not subdirectory)
│   ├── models/       # Beanie/MongoDB models
│   ├── services/     # Business logic
│   └── config/       # Settings, database config
├── data/
│   └── guidelines/   # WHO & MoH documents
├── tests/            # Test suite
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env   # Configure environment
```

## Run Development Server

```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/session` | Create chat session |
| POST | `/api/chat/message` | Send message & get AI response |
| POST | `/api/chat/stream` | SSE streaming response (auto-routes quick/full) |
| POST | `/api/chat/quick` | Quick single-turn response (lighter pipeline) |
| POST | `/api/chat/auto` | Auto-routed message (picks quick or full) |
| POST | `/api/chat/feedback` | Submit feedback on an assistant message |
| GET | `/api/chat/session/{session_id}/messages` | Get conversation history |
| GET | `/api/chat/sessions` | List all sessions for current user |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get health profile |
| PUT | `/api/profile` | Update profile |

### Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plans/current` | Get current plan |
| GET | `/api/plans/history` | Get plan history |
| POST | `/api/plans/feedback` | Submit adherence feedback |
