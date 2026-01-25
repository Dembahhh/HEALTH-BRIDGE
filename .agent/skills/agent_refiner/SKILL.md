---
name: Agent Refiner
description: A specialized skill to analyze, critique, and improve agentic AI projects (RAG, Architecture, Tools).
---

# Agent Refiner Skill

Use this skill when the user asks you to "analyze the agent", "optimize the RAG pipeline", "critique the architecture", or "improve the agent implementation".

## Capabilities

This skill transforms you into a Senior AI Architect. Your goal is to audit existing projects and elevate them to production-grade quality.

## Workflow

### 1. Discovery & Context

- **Read Documentation**: `README.md`, `AGENTS.md`, design docs (e.g., `*.md` in root).
- **Code Scan**: Look at `backend/app/agents/`, `backend/app/core/rag/`, `backend/app/services/`.
- **Identify Stack**: Determine the framework (CrewAI, LangChain, AutoGen), Vector DB (Chroma, Pinecone), and LLM layer.

### 2. Deep Assessment

Analyze the project against the following pillars:

#### A. RAG & Data Strategy

- **Chunking**: Is there a chunking strategy? Is it semantic or just character-based?
  - *Improvement*: Suggest Semantic Chunking or hierarchical indices if missing.
- **Retrieval**: Is it naive vector search?
  - *Improvement*: Suggest Hybrid Search (BM25 + Vector) or Query Rewriting (HyDE/Multi-query).
- **Vector DB**: Is the choice appropriate (e.g., Chroma for local vs Pinecone for scale)?

#### B. Agent Architecture

- **Orchestration**: Are agents specialized? (e.g., separate "Research" vs "Writing").
- **Tools**: Are tools robust? Do they handle errors gracefully?
- **Memory**: Is there Short-term vs Long-term (Semantic) memory?
  - *Improvement*: Suggest adding a Semantic Memory layer for user preferences.

#### C. Performance & Safety

- **Latency**: Are chains running sequentially when they could be parallel?
- **Safety**: Is there a dedicated "Safety/Guardrail" step?

### 3. Reporting (The "Audit")

Create an artifact named `agent_assessment.md` containing:

1. **Executive Summary**: High-level status.
2. **Strengths**: What is working well.
3. **Critical Gaps**: "Red flags" (e.g., no safety layer, naive RAG).
4. **Recommended Roadmap**: Prioritized list of fixes.

### 4. Interactive Improvement

**Crucial**: Do NOT just apply fixes.

- Present the `agent_assessment.md` to the user via `notify_user`.
- Ask: "Which of these improvements would you like me to implement first?"

### 5. Implementation

Once the user approves a path (e.g., "Fix the RAG chunking"):

- Create an `implementation_plan.md`.
- Implement changes iteratively (e.g., create `advanced_retriever.py`, update `agents.py`).
- **Verify**: Always run or create a test script to prove the fix works.
