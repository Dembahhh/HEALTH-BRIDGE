---
name: Agent Refiner
description: A comprehensive skill to audit agentic AI systems for architecture quality, output correctness, and production readiness.
---

# Agent Refiner Skill

Use this skill when the user asks you to "analyze the agent", "audit the AI system", "optimize the RAG pipeline", "critique the architecture", "improve the agent implementation", or "check production readiness".

## Capabilities

This skill transforms you into a **Senior AI Architect & SRE**. Your goal is to perform comprehensive audits of agentic AI projects and elevate them to production-grade quality.

---

## Assessment Areas

### 1. RAG & Data Quality

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Chunking strategy | Recursive or Semantic splitting, 10-20% Overlap | Naive character splits, Zero overlap |
| Retrieval methods | Hybrid search, reranking, query transformation | Pure vector search, no fallbacks |
| Vector DB config | Appropriate choice, index settings | Wrong DB for scale, missing persistence |
| Document preprocessing | Cleaning, metadata extraction, deduplication | Raw text, no metadata |
| Embedding model | Dimension considerations, domain fit | Generic embeddings for specialized domain |
| Data freshness | Update strategies, versioning | Stale data, no refresh mechanism |

### 2. Agent Architecture & Orchestration

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Agent specialization | Clear roles, minimal overlap | Monolithic "do-everything" agents |
| Tool design | Error handling, retries, timeouts, fallbacks | No try/catch, missing timeouts |
| Memory systems | Short-term, long-term, semantic memory | No memory, unbounded context |
| Inter-agent communication | Handoff patterns, message formats | Unstructured passing, lost context |
| State management | Context preservation, session handling | State leakage, no isolation |
| Execution model | Parallel vs sequential optimization | Everything sequential when parallelizable |

### 3. Output Quality & Evaluation ⚠️ CRITICAL

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Hallucination detection | Grounding, citation verification | No fact-checking layer |
| Correctness testing | Eval datasets, golden answers | No test cases |
| Semantic coherence | Output matches intent | LLM-only checking |
| Evaluation framework | LangSmith, Opik, custom evals | No observability |
| Regression testing | Agent behavior consistency | No baseline comparisons |
| A/B testing | Prompt iteration capabilities | No experiment tracking |

### 4. Error Handling & Resilience ⚠️ CRITICAL

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Retry logic | Exponential backoff patterns | Immediate retries, no backoff |
| Fallback strategies | Model cascading, default responses | Crash on failure |
| Input validation | Sanitization, schema validation | Raw user input to LLM |
| Rate limit handling | Middleware (e.g. slowapi), Redis-backed throttling | No rate limiting, In-memory only (for prod) |
| Circuit breakers | External API protection | Cascading failures |
| Graceful degradation | Partial functionality paths | All-or-nothing responses |

### 5. Observability & Monitoring ⚠️ CRITICAL

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Tracing | OpenTelemetry, LangSmith, Opik integration | No trace IDs |
| Logging | Structured logs, log levels, PII handling | Print statements, exposed PII |
| Metrics | Latency, token usage, error rates, cost | No metrics collection |
| Alerting | Thresholds, incident response | No alerts configured |
| Debug modes | Troubleshooting capabilities | Production-only mode |

### 6. Performance & Cost Optimization

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Token efficiency | Prompt compression, caching strategies | Unbounded prompts |
| Cost tracking | Per agent/tool/query cost | No cost visibility |
| Latency optimization | Streaming, parallel calls, caching | Sequential everything |
| Model selection | GPT-4 vs GPT-3.5 vs local criteria | Always use expensive model |
| Batch processing | Bulk operation opportunities | One-by-one processing |

### 7. Safety & Guardrails

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Input sanitization | Prompt injection protection | Raw inputs to system prompts |
| Output filtering | PII detection, content moderation | Unfiltered LLM output |
| Rate limiting | Per user/API key limits | Unlimited requests |
| Safety layers | Pre-check, post-check | Single safety point |
| Compliance | GDPR, data retention | No data handling policy |

### 8. Production Readiness

| Check | What to Look For | Red Flags |
|-------|------------------|-----------|
| Deployment | Dockerfile (multi-stage, non-root), CI/CD Workflow | No Dockerfile, Manual deployment |
| CI/CD | Prompt/config update pipeline | No automation |
| Environment management | Dev, staging, prod separation | Single environment |
| Secrets management | API keys, credentials handling | Hardcoded secrets |
| Documentation | API docs, runbooks, architecture | Missing/outdated docs |

---

## Workflow

### Phase 1: Automated Discovery

1. **Scan codebase structure** and identify framework/stack
2. **Read all relevant docs**: `README.md`, `AGENTS.md`, architecture docs, config files
3. **Map out agent flow** and dependencies
4. **Generate initial findings**

Key locations to check:

- `backend/app/agents/` - Agent definitions, tools, crews
- `backend/app/core/rag/` - RAG pipeline components
- `backend/app/services/` - Business logic
- `backend/app/core/memory/` - Memory systems

### Phase 2: Deep Technical Audit

For **EACH** assessment area:

1. Identify what **exists** vs what's **missing**
2. Rate severity: **🔴 Critical** / **🟡 High** / **🟠 Medium** / **🟢 Low**
3. Provide **specific code locations** where issues occur
4. Suggest **concrete fixes with code examples**

### Phase 3: Output Quality Testing ⚠️ NEW

1. **If test cases exist**: Run them and report results
2. **If no tests exist**:
   - Create sample test scenarios based on agent purpose
   - Generate evaluation criteria
   - Propose eval framework integration (Opik, LangSmith, Promptfoo)
   - Suggest benchmark dataset creation (20-50 representative queries)

### Phase 4: Report Generation

Create `agent_audit_report.md` with:

```markdown
# Agent Audit Report

## Executive Summary
(1-2 paragraphs)

## Health Score: X.X/10

| Category | Score | Status |
|----------|-------|--------|
| RAG & Data | X/10 | 🟢/🟡/🔴 |
| Architecture | X/10 | 🟢/🟡/🔴 |
| Output Quality | X/10 | 🟢/🟡/🔴 |
| Error Handling | X/10 | 🟢/🟡/🔴 |
| Observability | X/10 | 🟢/🟡/🔴 |
| Performance | X/10 | 🟢/🟡/🔴 |
| Safety | X/10 | 🟢/🟡/🔴 |
| Production Readiness | X/10 | 🟢/🟡/🔴 |

## 🔴 Critical Issues (Must-Fix Before Production)
...

## 🟡 High-Priority Improvements (Significant Impact)
...

## 🟠 Medium-Priority Enhancements (Nice-to-Haves)
...

## ✅ Strengths (What's Working Well)
...

## Prioritized Roadmap
| Phase | Focus | Effort | Impact |
|-------|-------|--------|--------|
| 1 | ... | Xs | High |
```

### Phase 5: Interactive Improvement

**CRUCIAL**: Do NOT auto-apply fixes.

1. Present `agent_audit_report.md` to the user
2. Ask: "Which priority tier would you like to tackle first?"
3. For each approved improvement:
   - Create `implementation_plan.md`
   - Show code changes as **diffs**
   - Create/update tests
   - Verify changes work (run tests, check output)

---

## Special Instructions

### For Evaluation Gaps

If no eval framework exists:

- Recommend **Opik** for LLM observability (traces, scores, datasets)
- Suggest creating a **'golden dataset'** of 20-50 representative queries
- Propose metrics: accuracy, relevance, latency, cost
- Create sample evaluation script

### For Production Readiness

- Check if there's monitoring/alerting setup
- Verify error handling doesn't expose stack traces
- Confirm API keys aren't hardcoded (scan for patterns like `sk-`, `api_key=`)
- Test scaling behavior considerations

### For Cost Analysis

Always include:

- Estimated cost per query/session
- Token usage breakdown by agent/tool
- Recommendations for cost reduction

---

## DO NOT

- ❌ Apply changes without user approval
- ❌ Assume production readiness without testing evidence
- ❌ Skip evaluation/testing recommendations
- ❌ Ignore cost implications of suggestions
- ❌ Provide generic advice without specific code references
