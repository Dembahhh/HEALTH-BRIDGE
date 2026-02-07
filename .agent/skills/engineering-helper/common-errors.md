# Common AI/ML Error Patterns and Solutions

Quick reference for frequently encountered errors in AI/LLM applications.

---

## LangChain Errors

### `OutputParserException: Could not parse LLM output`
**Cause**: LLM response doesn't match expected format (JSON, structured output)
**Solutions**:
```python
# 1. Use output_fixing_parser
from langchain.output_parsers import OutputFixingParser
fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=llm)

# 2. Use PydanticOutputParser with retry
from langchain.output_parsers import PydanticOutputParser, RetryWithErrorOutputParser
retry_parser = RetryWithErrorOutputParser.from_llm(parser=parser, llm=llm)

# 3. Use with_structured_output (recommended for newer versions)
structured_llm = llm.with_structured_output(MyPydanticModel)
```

### `ValidationError: 1 validation error for ChatOpenAI`
**Cause**: Missing or invalid API key
**Solutions**:
```python
# Check environment variable
import os
print(os.getenv("OPENAI_API_KEY"))  # Should not be None

# Or pass explicitly
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(api_key="sk-...")
```

### `RateLimitError` / `429 Too Many Requests`
**Cause**: Exceeding API rate limits
**Solutions**:
```python
# 1. Add exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=60))
def call_llm(prompt):
    return llm.invoke(prompt)

# 2. Use max_retries parameter
llm = ChatOpenAI(max_retries=3)

# 3. Implement request queuing with rate limiting
from langchain.callbacks import get_openai_callback
```

### `ContextWindowExceeded` / Token Limit Errors
**Cause**: Input + output exceeds model's context window
**Solutions**:
```python
# 1. Use text splitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)

# 2. Summarize before processing
from langchain.chains.summarize import load_summarize_chain

# 3. Use map-reduce for long documents
chain = load_summarize_chain(llm, chain_type="map_reduce")
```

---

## OpenAI SDK Errors

### `openai.BadRequestError: maximum context length exceeded`
**Cause**: Too many tokens in request
**Solutions**:
```python
import tiktoken

def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def truncate_to_limit(text, max_tokens=8000, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return encoding.decode(tokens)
```

### `openai.AuthenticationError: Invalid API key`
**Cause**: API key is invalid, expired, or wrong format
**Solutions**:
```python
# 1. Verify key format (should start with sk-)
# 2. Check organization ID if using org-specific key
client = OpenAI(
    api_key="sk-...",
    organization="org-..."  # If applicable
)

# 3. For Azure OpenAI
from openai import AzureOpenAI
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

### `openai.APITimeoutError`
**Cause**: Request took too long
**Solutions**:
```python
# Increase timeout
client = OpenAI(timeout=60.0)

# Or per-request
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    timeout=120.0
)
```

---

## Anthropic SDK Errors

### `anthropic.BadRequestError: prompt is too long`
**Cause**: Exceeding Claude's context window
**Solutions**:
```python
# 1. Use prompt caching for repeated content
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "Long system prompt...",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[...]
)

# 2. Summarize or chunk long inputs
```

### `anthropic.APIStatusError: 529 Overloaded`
**Cause**: API is temporarily overloaded
**Solutions**:
```python
from anthropic import Anthropic
import time

client = Anthropic()

def call_with_retry(messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=messages
            )
        except Exception as e:
            if "529" in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
```

---

## ChromaDB Errors

### `chromadb.errors.InvalidDimensionException`
**Cause**: Embedding dimensions don't match collection
**Solutions**:
```python
# 1. Check embedding dimensions
embeddings = embedding_function(["test"])
print(f"Embedding dimension: {len(embeddings[0])}")

# 2. Create new collection with correct dimensions
# Or delete and recreate
client.delete_collection("my_collection")
collection = client.create_collection(
    name="my_collection",
    embedding_function=embedding_function
)
```

### `sqlite3.OperationalError: database is locked`
**Cause**: Multiple processes accessing same DB
**Solutions**:
```python
# 1. Use client-server mode for production
import chromadb
client = chromadb.HttpClient(host="localhost", port=8000)

# 2. Or use different paths for different processes
client = chromadb.PersistentClient(path=f"./chroma_db_{process_id}")
```

### `Collection.query() got unexpected keyword argument`
**Cause**: API change between versions
**Solutions**:
```python
# Old API (pre-0.4.0)
results = collection.query(query_texts=["query"], n_results=5)

# New API (0.4.0+)
results = collection.query(
    query_texts=["query"],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)
```

---

## Hugging Face Errors

### `OutOfMemoryError: CUDA out of memory`
**Cause**: Model too large for GPU memory
**Solutions**:
```python
# 1. Use quantization
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)
model = AutoModelForCausalLM.from_pretrained(
    "model_name",
    quantization_config=quantization_config,
    device_map="auto"
)

# 2. Use device_map for automatic distribution
model = AutoModelForCausalLM.from_pretrained(
    "model_name",
    device_map="auto",
    torch_dtype=torch.float16
)

# 3. Enable gradient checkpointing for training
model.gradient_checkpointing_enable()

# 4. Reduce batch size
```

### `ValueError: text input must of type str`
**Cause**: Passing wrong type to tokenizer
**Solutions**:
```python
# Ensure text is string
text = str(text) if text is not None else ""

# For batches, ensure list of strings
texts = [str(t) for t in texts if t is not None]
```

### `RuntimeError: Expected all tensors to be on the same device`
**Cause**: Model and inputs on different devices
**Solutions**:
```python
# Move inputs to same device as model
device = model.device
inputs = tokenizer(text, return_tensors="pt").to(device)

# Or use device_map
model = AutoModel.from_pretrained("model", device_map="auto")
```

---

## CrewAI Errors

### `ValidationError: agent must have a role`
**Cause**: Missing required agent configuration
**Solutions**:
```python
from crewai import Agent

agent = Agent(
    role="Researcher",  # Required
    goal="Find accurate information",  # Required
    backstory="Expert researcher...",  # Required
    llm=llm,
    tools=[search_tool]
)
```

### `Task output not matching expected format`
**Cause**: Agent output doesn't match `output_pydantic`
**Solutions**:
```python
from crewai import Task
from pydantic import BaseModel

class ExpectedOutput(BaseModel):
    summary: str
    key_points: list[str]

task = Task(
    description="Analyze the document...",
    expected_output="A summary with key points",
    output_pydantic=ExpectedOutput,
    agent=agent
)

# Add explicit instructions in description
task = Task(
    description="""Analyze the document and return JSON:
    {"summary": "...", "key_points": ["point1", "point2"]}""",
    ...
)
```

---

## LlamaIndex Errors

### `ValueError: No service context or llm provided`
**Cause**: LLM not configured for index operations
**Solutions**:
```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

# Global settings (recommended)
Settings.llm = OpenAI(model="gpt-4")
Settings.embed_model = "local:BAAI/bge-small-en-v1.5"

# Or per-index
index = VectorStoreIndex.from_documents(
    documents,
    llm=OpenAI(model="gpt-4")
)
```

### `Empty response from query engine`
**Cause**: No relevant documents found or retrieval issue
**Solutions**:
```python
# 1. Check retrieval results
retriever = index.as_retriever(similarity_top_k=10)
nodes = retriever.retrieve("query")
print(f"Found {len(nodes)} nodes")

# 2. Lower similarity threshold
query_engine = index.as_query_engine(
    similarity_top_k=10,
    response_mode="tree_summarize"
)

# 3. Check embedding model consistency
```

---

## PyTorch Errors

### `RuntimeError: CUDA error: device-side assert triggered`
**Cause**: Usually index out of bounds or invalid tensor operation
**Solutions**:
```python
# 1. Run with CUDA_LAUNCH_BLOCKING for better error messages
import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

# 2. Check tensor indices
assert all(idx < num_classes for idx in labels), "Label index out of bounds"

# 3. Validate input shapes
print(f"Input shape: {x.shape}, Expected: ...")
```

### `RuntimeError: Trying to backward through the graph a second time`
**Cause**: Calling backward() without retain_graph=True
**Solutions**:
```python
# If you need to backward multiple times
loss.backward(retain_graph=True)

# Or detach intermediate tensors
output = model(x)
loss1 = criterion1(output.detach(), target1)
loss2 = criterion2(output, target2)
```

---

## General Python/ML Errors

### `ModuleNotFoundError` after pip install
**Cause**: Wrong Python environment or package not installed correctly
**Solutions**:
```bash
# Check which Python
which python
python -c "import sys; print(sys.executable)"

# Install in correct environment
python -m pip install package_name

# For Jupyter
!{sys.executable} -m pip install package_name
```

### Memory Leak in Long-Running Applications
**Cause**: Accumulated tensors, caches, or references
**Solutions**:
```python
# 1. Clear CUDA cache periodically
import torch
torch.cuda.empty_cache()

# 2. Delete unused variables
del large_tensor
import gc
gc.collect()

# 3. Use context managers
with torch.no_grad():
    # inference code

# 4. Limit cache sizes
from functools import lru_cache
@lru_cache(maxsize=100)  # Limit cache size
def cached_function(x):
    ...
```

---

## Quick Debugging Checklist

1. **Version Check**: `pip show package_name`
2. **Environment**: `python -c "import sys; print(sys.version)"`
3. **GPU Status**: `nvidia-smi` or `torch.cuda.is_available()`
4. **API Key**: Check environment variables are set
5. **Network**: Can you reach the API endpoint?
6. **Logs**: Enable verbose/debug logging
7. **Minimal Reproduction**: Can you reproduce with minimal code?
