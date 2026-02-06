# Curated AI/ML Resources

Authoritative sources for AI/ML engineering, prioritized by reliability and recency.

---

## Official Documentation (Primary Sources)

### LLM Frameworks

| Framework | Documentation | GitHub | Version Notes |
|-----------|--------------|--------|---------------|
| **LangChain** | [python.langchain.com](https://python.langchain.com/docs/) | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | Check migration guides for 0.1→0.2→0.3 |
| **LlamaIndex** | [docs.llamaindex.ai](https://docs.llamaindex.ai/) | [run-llama/llama_index](https://github.com/run-llama/llama_index) | Major API changes in 0.10+ |
| **CrewAI** | [docs.crewai.com](https://docs.crewai.com/) | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | Rapidly evolving |
| **Haystack** | [docs.haystack.deepset.ai](https://docs.haystack.deepset.ai/) | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | v2.0 is major rewrite |
| **Semantic Kernel** | [learn.microsoft.com/semantic-kernel](https://learn.microsoft.com/en-us/semantic-kernel/) | [microsoft/semantic-kernel](https://github.com/microsoft/semantic-kernel) | Multi-language support |

### Model Provider SDKs

| Provider | Documentation | API Reference | Changelog |
|----------|--------------|---------------|-----------|
| **OpenAI** | [platform.openai.com/docs](https://platform.openai.com/docs/) | [API Reference](https://platform.openai.com/docs/api-reference) | [Changelog](https://platform.openai.com/docs/changelog) |
| **Anthropic** | [docs.anthropic.com](https://docs.anthropic.com/) | [API Reference](https://docs.anthropic.com/en/api) | Check for new features |
| **Google AI** | [ai.google.dev/docs](https://ai.google.dev/docs) | [API Reference](https://ai.google.dev/api) | Gemini updates frequently |
| **Cohere** | [docs.cohere.com](https://docs.cohere.com/) | [API Reference](https://docs.cohere.com/reference) | Command R+ focus |
| **Mistral** | [docs.mistral.ai](https://docs.mistral.ai/) | [API Reference](https://docs.mistral.ai/api/) | Open models available |

### ML Frameworks

| Framework | Documentation | Tutorials | Best For |
|-----------|--------------|-----------|----------|
| **PyTorch** | [pytorch.org/docs](https://pytorch.org/docs/stable/) | [Tutorials](https://pytorch.org/tutorials/) | Research, flexibility |
| **Hugging Face** | [huggingface.co/docs](https://huggingface.co/docs) | [Course](https://huggingface.co/learn) | Transformers, fine-tuning |
| **TensorFlow** | [tensorflow.org/api_docs](https://www.tensorflow.org/api_docs/python/) | [Tutorials](https://www.tensorflow.org/tutorials) | Production, TPU |
| **JAX** | [jax.readthedocs.io](https://jax.readthedocs.io/) | [Tutorials](https://jax.readthedocs.io/en/latest/tutorials.html) | High-performance research |

### Vector Databases

| Database | Documentation | Quickstart | Best For |
|----------|--------------|------------|----------|
| **ChromaDB** | [docs.trychroma.com](https://docs.trychroma.com/) | [Getting Started](https://docs.trychroma.com/getting-started) | Prototyping, local dev |
| **Pinecone** | [docs.pinecone.io](https://docs.pinecone.io/) | [Quickstart](https://docs.pinecone.io/docs/quickstart) | Production, managed |
| **Weaviate** | [weaviate.io/developers](https://weaviate.io/developers/weaviate) | [Quickstart](https://weaviate.io/developers/weaviate/quickstart) | Hybrid search, GraphQL |
| **Qdrant** | [qdrant.tech/documentation](https://qdrant.tech/documentation/) | [Quickstart](https://qdrant.tech/documentation/quick-start/) | Rust performance |
| **Milvus** | [milvus.io/docs](https://milvus.io/docs/) | [Quickstart](https://milvus.io/docs/quickstart.md) | Scalability |
| **pgvector** | [github.com/pgvector](https://github.com/pgvector/pgvector) | [README](https://github.com/pgvector/pgvector#readme) | PostgreSQL integration |

---

## Technical Blogs (High-Quality Analysis)

### Data Science & ML

| Source | Focus | Quality | URL |
|--------|-------|---------|-----|
| **Daily Dose of Data Science** | Practical ML tips | Excellent | [dailydoseofds.com](https://www.dailydoseofds.com/) |
| **Neptune.ai Blog** | MLOps, experiment tracking | Excellent | [neptune.ai/blog](https://neptune.ai/blog) |
| **Towards Data Science** | Broad ML coverage | Good (varies) | [towardsdatascience.com](https://towardsdatascience.com/) |
| **Analytics Vidhya** | Tutorials, competitions | Good | [analyticsvidhya.com](https://www.analyticsvidhya.com/blog/) |
| **Machine Learning Mastery** | Fundamentals, tutorials | Excellent | [machinelearningmastery.com](https://machinelearningmastery.com/) |

### LLM & AI Engineering

| Source | Focus | Quality | URL |
|--------|-------|---------|-----|
| **Simon Willison's Blog** | LLM tools, prompt eng | Excellent | [simonwillison.net](https://simonwillison.net/) |
| **Lilian Weng's Blog** | Deep technical analysis | Excellent | [lilianweng.github.io](https://lilianweng.github.io/) |
| **Chip Huyen's Blog** | MLOps, production ML | Excellent | [huyenchip.com](https://huyenchip.com/blog/) |
| **Eugene Yan's Blog** | RecSys, ML systems | Excellent | [eugeneyan.com](https://eugeneyan.com/) |
| **The Gradient** | Research summaries | Excellent | [thegradient.pub](https://thegradient.pub/) |
| **Ahead of AI** | LLM research updates | Excellent | [magazine.sebastianraschka.com](https://magazine.sebastianraschka.com/) |

### Company Engineering Blogs

| Company | Focus | URL |
|---------|-------|-----|
| **OpenAI** | Research, announcements | [openai.com/blog](https://openai.com/blog) |
| **Anthropic** | Research, safety | [anthropic.com/research](https://www.anthropic.com/research) |
| **Google DeepMind** | Research | [deepmind.google/research](https://deepmind.google/research/) |
| **Meta AI** | Open research | [ai.meta.com/blog](https://ai.meta.com/blog/) |
| **Hugging Face** | Tools, models | [huggingface.co/blog](https://huggingface.co/blog) |
| **Weights & Biases** | MLOps | [wandb.ai/fully-connected](https://wandb.ai/fully-connected) |

---

## Community Resources

### GitHub Repositories

| Type | Where to Search | Tips |
|------|-----------------|------|
| **Issues** | `github.com/{org}/{repo}/issues` | Search closed issues for solutions |
| **Discussions** | `github.com/{org}/{repo}/discussions` | Community Q&A, best practices |
| **Examples** | Look for `/examples` or `/cookbook` folders | Official usage patterns |
| **Awesome Lists** | Search "awesome-{topic}" | Curated resource collections |

### Key Awesome Lists
- [awesome-langchain](https://github.com/kyrolabs/awesome-langchain)
- [awesome-llm](https://github.com/Hannibal046/Awesome-LLM)
- [awesome-production-machine-learning](https://github.com/EthicalML/awesome-production-machine-learning)
- [awesome-mlops](https://github.com/visenger/awesome-mlops)

### Stack Overflow

**Search Tips:**
```
[langchain] error message
[openai-api] rate limit
[pytorch] cuda out of memory
```

**Quality Indicators:**
- Check answer date (AI/ML evolves fast)
- Look for accepted answers with recent activity
- Verify against official docs

### Discord & Slack Communities

| Community | Focus | Join |
|-----------|-------|------|
| **LangChain Discord** | LangChain help | [discord.gg/langchain](https://discord.gg/langchain) |
| **Hugging Face Discord** | HF ecosystem | [discord.gg/huggingface](https://discord.gg/huggingface) |
| **MLOps Community Slack** | MLOps practices | [mlops.community](https://mlops.community/) |
| **Weights & Biases Discord** | W&B, ML | [wandb.ai/discord](https://wandb.ai/discord) |

---

## Research & Papers

### Where to Find Papers

| Source | Best For | URL |
|--------|----------|-----|
| **arXiv (cs.CL, cs.LG)** | Latest research | [arxiv.org](https://arxiv.org/) |
| **Papers With Code** | Papers + implementations | [paperswithcode.com](https://paperswithcode.com/) |
| **Semantic Scholar** | Paper search & citations | [semanticscholar.org](https://www.semanticscholar.org/) |
| **Google Scholar** | Comprehensive search | [scholar.google.com](https://scholar.google.com/) |
| **Hugging Face Papers** | Daily paper summaries | [huggingface.co/papers](https://huggingface.co/papers) |

### Key Papers to Know

**Transformers & Attention:**
- "Attention Is All You Need" (Vaswani et al., 2017)
- "BERT: Pre-training of Deep Bidirectional Transformers" (Devlin et al., 2018)

**LLMs:**
- "Language Models are Few-Shot Learners" (GPT-3, Brown et al., 2020)
- "Training language models to follow instructions" (InstructGPT, Ouyang et al., 2022)
- "Constitutional AI" (Anthropic, Bai et al., 2022)

**RAG & Retrieval:**
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "Dense Passage Retrieval" (Karpukhin et al., 2020)

**Agents:**
- "ReAct: Synergizing Reasoning and Acting" (Yao et al., 2022)
- "Toolformer" (Schick et al., 2023)

---

## Video Resources

### YouTube Channels

| Channel | Focus | Quality |
|---------|-------|---------|
| **Andrej Karpathy** | Deep learning fundamentals | Excellent |
| **Yannic Kilcher** | Paper explanations | Excellent |
| **Two Minute Papers** | Research summaries | Good |
| **Sentdex** | Practical Python ML | Good |
| **DeepLearning.AI** | Courses, tutorials | Excellent |

### Courses

| Course | Platform | Cost |
|--------|----------|------|
| **Fast.ai** | fast.ai | Free |
| **DeepLearning.AI Specializations** | Coursera | Paid/Audit free |
| **Stanford CS229, CS231n** | YouTube | Free |
| **Hugging Face Course** | HF | Free |

---

## Search Strategies

### For Framework-Specific Issues
```
"{framework} {error_message}" site:github.com
"{framework} {feature}" site:stackoverflow.com
"{framework} docs {topic}"
```

### For Recent Information
```
"{topic}" after:2024-01-01
"{framework} {feature}" 2024 OR 2025
```

### For Production Guidance
```
"{framework} production deployment"
"{topic}" best practices MLOps
"{framework} at scale"
```

### For Comparisons
```
"{framework_a} vs {framework_b}" 2024
"{tool_a}" compared to "{tool_b}"
"when to use {framework}"
```

---

## Quality Assessment Checklist

When evaluating a source:

1. **Recency**: Is it from the last 12 months? (Critical for AI/ML)
2. **Author**: Domain expert or credible organization?
3. **Verification**: Does it cite official docs or papers?
4. **Reproducibility**: Does it include working code?
5. **Version Awareness**: Does it mention library versions?
6. **Production Focus**: Does it consider real-world constraints?
