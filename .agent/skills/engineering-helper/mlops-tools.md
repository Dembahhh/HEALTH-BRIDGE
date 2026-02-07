# MLOps Tools Quick Reference

Practical guide to observability, evaluation, and deployment tools for AI/LLM applications.

---

## LLM Observability & Tracing

### Opik (Comet ML)

**Best For**: LLM tracing, evaluation, prompt management

```python
# Installation
pip install opik

# Basic Setup
import opik
opik.configure(api_key="your-api-key")

# Trace LLM calls
from opik import track

@track
def generate_response(prompt: str) -> str:
    response = llm.invoke(prompt)
    return response

# Track with metadata
@track(name="chat_completion", tags=["production"])
def chat(messages: list) -> str:
    return llm.invoke(messages)

# Manual tracing
from opik import Opik
client = Opik()

trace = client.trace(
    name="my_llm_call",
    input={"prompt": prompt},
    output={"response": response},
    metadata={"model": "gpt-4", "temperature": 0.7}
)

# Evaluation
from opik.evaluation import evaluate
from opik.evaluation.metrics import Hallucination, AnswerRelevance

results = evaluate(
    dataset=test_dataset,
    task=my_llm_task,
    scoring_metrics=[Hallucination(), AnswerRelevance()]
)
```

**Key Features**:
- Automatic tracing with decorators
- LangChain/LlamaIndex integrations
- Built-in evaluation metrics
- Prompt versioning
- Cost tracking

**Documentation**: [comet.com/docs/opik](https://www.comet.com/docs/opik/)

---

### LangSmith

**Best For**: LangChain applications, debugging chains/agents

```python
# Setup (environment variables)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your-api-key
export LANGCHAIN_PROJECT=my-project

# Python setup
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"

# Automatic tracing (no code changes needed!)
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()
response = llm.invoke("Hello")  # Automatically traced

# Manual tracing
from langsmith import Client
client = Client()

# Create dataset for evaluation
dataset = client.create_dataset("my-eval-dataset")
client.create_examples(
    inputs=[{"question": "What is 2+2?"}],
    outputs=[{"answer": "4"}],
    dataset_id=dataset.id
)

# Run evaluation
from langchain.smith import run_on_dataset
results = run_on_dataset(
    client=client,
    dataset_name="my-eval-dataset",
    llm_or_chain_factory=lambda: my_chain
)
```

**Key Features**:
- Zero-config tracing for LangChain
- Dataset management
- Online evaluation
- Prompt playground
- Hub for sharing prompts

**Documentation**: [docs.smith.langchain.com](https://docs.smith.langchain.com/)

---

### Weights & Biases (W&B)

**Best For**: Experiment tracking, model training, sweeps

```python
# Installation
pip install wandb

# Initialize
import wandb
wandb.init(project="my-llm-project")

# Log metrics
wandb.log({
    "loss": 0.5,
    "accuracy": 0.92,
    "latency_ms": 150
})

# Log LLM traces
from wandb.integration.openai import autolog
autolog({"project": "my-project"})  # Auto-logs OpenAI calls

# Track prompts
wandb.log({
    "prompt": wandb.Html(f"<pre>{prompt}</pre>"),
    "response": wandb.Html(f"<pre>{response}</pre>"),
    "tokens": token_count
})

# Hyperparameter sweeps
sweep_config = {
    "method": "bayes",
    "metric": {"name": "accuracy", "goal": "maximize"},
    "parameters": {
        "temperature": {"min": 0.0, "max": 1.0},
        "max_tokens": {"values": [256, 512, 1024]}
    }
}
sweep_id = wandb.sweep(sweep_config, project="my-project")
wandb.agent(sweep_id, function=train)

# Artifacts (save models, datasets)
artifact = wandb.Artifact("model", type="model")
artifact.add_file("model.pkl")
wandb.log_artifact(artifact)
```

**Key Features**:
- Experiment tracking
- Hyperparameter optimization (sweeps)
- Model versioning (artifacts)
- Team collaboration
- Rich visualizations

**Documentation**: [docs.wandb.ai](https://docs.wandb.ai/)

---

### MLflow

**Best For**: Experiment tracking, model registry, deployment

```python
# Installation
pip install mlflow

# Basic tracking
import mlflow

mlflow.set_experiment("my-experiment")

with mlflow.start_run():
    # Log parameters
    mlflow.log_param("model", "gpt-4")
    mlflow.log_param("temperature", 0.7)

    # Log metrics
    mlflow.log_metric("latency", 0.5)
    mlflow.log_metric("accuracy", 0.92)

    # Log artifacts
    mlflow.log_artifact("prompt_template.txt")

    # Log model
    mlflow.pyfunc.log_model("model", python_model=my_model)

# LLM-specific tracking (MLflow 2.8+)
from mlflow.llm import log_predictions

log_predictions(
    inputs=["What is ML?"],
    outputs=["Machine learning is..."],
    prompts=["Answer the question: {input}"]
)

# Model registry
mlflow.register_model("runs:/abc123/model", "my-model")

# Load and serve
model = mlflow.pyfunc.load_model("models:/my-model/Production")

# Start tracking server
# mlflow server --host 0.0.0.0 --port 5000
```

**Key Features**:
- Open source
- Model registry with stages
- Deployment integrations
- Language agnostic
- Self-hosted or managed (Databricks)

**Documentation**: [mlflow.org/docs](https://mlflow.org/docs/latest/)

---

## Evaluation Tools

### RAGAS (RAG Evaluation)

**Best For**: Evaluating RAG pipelines

```python
pip install ragas

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset

# Prepare evaluation data
eval_data = {
    "question": ["What is X?"],
    "answer": ["X is..."],
    "contexts": [["Context 1", "Context 2"]],
    "ground_truth": ["X is actually..."]
}
dataset = Dataset.from_dict(eval_data)

# Run evaluation
results = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ]
)
print(results)
```

**Metrics Explained**:
- **Faithfulness**: Is the answer grounded in the context?
- **Answer Relevancy**: Does the answer address the question?
- **Context Precision**: Are retrieved contexts relevant?
- **Context Recall**: Are all needed facts retrieved?

**Documentation**: [docs.ragas.io](https://docs.ragas.io/)

---

### DeepEval

**Best For**: Comprehensive LLM evaluation

```python
pip install deepeval

from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
    ToxicityMetric
)
from deepeval.test_case import LLMTestCase

# Create test case
test_case = LLMTestCase(
    input="What is the capital of France?",
    actual_output="The capital of France is Paris.",
    expected_output="Paris",
    context=["France is a country in Europe. Its capital is Paris."]
)

# Define metrics
metrics = [
    AnswerRelevancyMetric(threshold=0.7),
    FaithfulnessMetric(threshold=0.7),
    HallucinationMetric(threshold=0.5),
]

# Run evaluation
results = evaluate([test_case], metrics)

# Pytest integration
from deepeval import assert_test

def test_llm_output():
    assert_test(test_case, metrics)
```

**Documentation**: [docs.confident-ai.com](https://docs.confident-ai.com/)

---

## Deployment & Serving

### Quick Comparison

| Tool | Best For | Scaling | Cost |
|------|----------|---------|------|
| **FastAPI + Uvicorn** | Simple APIs | Manual | Low |
| **Ray Serve** | ML inference at scale | Auto | Medium |
| **BentoML** | Model packaging & serving | Auto | Medium |
| **vLLM** | High-throughput LLM serving | Auto | Medium |
| **TGI (Text Gen Inference)** | HF model serving | Auto | Medium |
| **Modal** | Serverless ML | Auto | Pay-per-use |
| **Replicate** | Model hosting | Managed | Pay-per-use |

### FastAPI (Simple Deployment)

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    text: str

class Response(BaseModel):
    result: str
    latency_ms: float

@app.post("/generate", response_model=Response)
async def generate(query: Query):
    import time
    start = time.time()
    result = llm.invoke(query.text)
    latency = (time.time() - start) * 1000
    return Response(result=result, latency_ms=latency)

# Run: uvicorn main:app --host 0.0.0.0 --port 8000
```

### vLLM (High-Throughput LLM Serving)

```python
# Installation
pip install vllm

# Start server
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000

# Use OpenAI-compatible client
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**Documentation**: [docs.vllm.ai](https://docs.vllm.ai/)

---

## Monitoring & Alerting

### Prometheus + Grafana

```python
# Add metrics to your app
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
REQUEST_COUNT = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "status"]
)

LATENCY = Histogram(
    "llm_request_latency_seconds",
    "LLM request latency",
    ["model"]
)

# Use in your code
def call_llm(prompt: str):
    with LATENCY.labels(model="gpt-4").time():
        try:
            result = llm.invoke(prompt)
            REQUEST_COUNT.labels(model="gpt-4", status="success").inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(model="gpt-4", status="error").inc()
            raise

# Start metrics server
start_http_server(8001)  # Prometheus scrapes this
```

### Key Metrics to Track

| Metric | Type | Why It Matters |
|--------|------|----------------|
| `llm_requests_total` | Counter | Traffic volume |
| `llm_request_latency_seconds` | Histogram | Performance (P50, P95, P99) |
| `llm_tokens_total` | Counter | Cost tracking |
| `llm_errors_total` | Counter | Reliability |
| `llm_rate_limit_hits` | Counter | Capacity issues |
| `retrieval_relevance_score` | Gauge | RAG quality |

---

## Cost Management

### Token Counting

```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def estimate_cost(prompt: str, response: str, model: str = "gpt-4") -> float:
    # Pricing as of 2024 (check current prices!)
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }

    input_tokens = count_tokens(prompt, model)
    output_tokens = count_tokens(response, model)

    prices = pricing.get(model, {"input": 0.01, "output": 0.03})
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1000

    return cost
```

### Cost Optimization Strategies

1. **Caching**: Cache identical prompts
2. **Model Selection**: Use smaller models for simple tasks
3. **Prompt Compression**: Remove unnecessary tokens
4. **Batching**: Batch similar requests
5. **Streaming**: Stream for better UX (same cost)

---

## Tool Selection Guide

### By Use Case

| Use Case | Recommended Tools |
|----------|-------------------|
| **LLM Tracing (General)** | Opik, LangSmith |
| **LangChain Apps** | LangSmith (native) |
| **Model Training** | W&B, MLflow |
| **RAG Evaluation** | RAGAS, DeepEval |
| **Production Monitoring** | Prometheus + Grafana |
| **High-Throughput Serving** | vLLM, TGI |
| **Quick Prototypes** | FastAPI |
| **Serverless** | Modal, Replicate |

### By Team Size

| Team Size | Stack Recommendation |
|-----------|---------------------|
| **Solo/Small** | Opik + FastAPI + SQLite |
| **Medium** | LangSmith + MLflow + PostgreSQL |
| **Large** | W&B + Custom metrics + K8s |

### By Budget

| Budget | Recommendation |
|--------|----------------|
| **Free** | MLflow (self-hosted) + Prometheus |
| **Low** | Opik free tier + basic monitoring |
| **Medium** | LangSmith/W&B paid tiers |
| **Enterprise** | Full observability stack + dedicated support |

---

## Quick Start Checklist

### Minimum Viable MLOps

- [ ] **Tracing**: Add `@track` decorators to LLM calls
- [ ] **Logging**: Structured logs with request IDs
- [ ] **Metrics**: Track latency, tokens, errors
- [ ] **Evaluation**: Create golden dataset, run periodic evals
- [ ] **Alerting**: Alert on error rate > threshold
- [ ] **Cost**: Track daily/weekly spend

### Production Readiness

- [ ] All LLM calls traced
- [ ] P95 latency < target
- [ ] Error rate < 1%
- [ ] Evaluation score > baseline
- [ ] Cost within budget
- [ ] Alerts configured
- [ ] Runbooks documented
