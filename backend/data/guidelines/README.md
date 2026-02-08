# Health Guidelines for RAG (Retrieval-Augmented Generation)

This directory contains medical guideline documents that are indexed into ChromaDB and used by the HealthBridge AI agents to provide evidence-based health advice. These documents are the knowledge foundation for the system's RAG pipeline.

## How Guidelines Feed Into the AI Agents

```
data/guidelines/*.md
        |
        v
  GuidelineIndexer          (app/core/rag/indexer.py)
    - Reads each .md/.txt file
    - Auto-detects metadata from filename
    - Chunks text via DocumentChunker (app/core/rag/chunker.py)
        |
        v
  SentenceTransformers      (all-MiniLM-L6-v2 embedding model)
    - Converts chunks to 384-dim vectors
        |
        v
  ChromaDB Collection       ("guidelines" collection, persisted to data/chroma/)
    - Stores vectors + metadata (condition, topic, source)
        |
        v
  VectorRetriever            (app/core/rag/retriever.py)
    - retrieve_guidelines(query, condition, topic) -> ranked chunks
        |
        v
  CrewAI Agent Tools         (app/agents/agents.py)
    - risk_guideline_agent:  uses retrieve_guidelines for risk assessments
    - safety_policy_agent:   uses retrieve_guidelines for red flag verification
        |
        v
  Corrective RAG Critic      (app/core/rag/critic.py)
    - Validates that agent claims are supported by retrieved evidence
    - Retries retrieval if confidence < 0.6
```

The more comprehensive and accurate the guideline documents, the better the agents can:
- Provide WHO-aligned dietary and activity recommendations
- Identify emergency red flags and escalate appropriately
- Account for social determinants of health (SDOH) in low-resource settings
- Stratify cardiovascular risk using validated screening thresholds
- Offer culturally appropriate advice for African settings

## Guideline Files

### Filename Convention

Files follow the pattern: `{source}_{condition}_{topic}.md`

The indexer auto-parses metadata from this convention. No code changes are needed when adding new files — just follow the naming pattern.

| Component   | Values                                      |
|-------------|---------------------------------------------|
| `source`    | `who` (WHO), `moh` (Ministry of Health)     |
| `condition` | `hypertension`, `diabetes`, `general_ncd`   |
| `topic`     | `diet`, `activity`, `red_flags`, `sdoh`, `risk_factors` |

### Current Files

| File | Source | Condition | Topic | Description |
|------|--------|-----------|-------|-------------|
| `who_hypertension_diet.md` | WHO | hypertension | diet | Sodium reduction (<2g/day), DASH diet, potassium sources, Africa-specific affordable alternatives |
| `who_hypertension_activity.md` | WHO | hypertension | activity | 150-300 min/week targets, exercise types, safety considerations, starting from sedentary, contraindications |
| `who_diabetes_diet.md` | WHO | diabetes | diet | Sugar <10% energy, glycemic index, fiber 25-30g/day, meal timing, BMI thresholds, beverage guidance |
| `who_diabetes_activity.md` | WHO | diabetes | activity | Insulin sensitivity, post-meal exercise timing, foot care during exercise, hypoglycemia monitoring |
| `who_general_ncd_red_flags.md` | WHO | general_ncd | red_flags | Hypertensive crisis, FAST stroke protocol, heart attack signs, DKA/HHS, severe hypoglycemia, diabetic foot emergency, urgent vs emergency triage |
| `who_general_ncd_risk_factors.md` | WHO | general_ncd | risk_factors | Modifiable/non-modifiable risk factors, risk synergy, WHO HEARTS package (H-E-A-R-T-S), screening thresholds (BP, glucose, BMI, waist), prevention by risk level |
| `moh_general_ncd_sdoh.md` | MoH | general_ncd | sdoh | SDOH barriers in African settings, food-on-a-budget strategies, exercise with safety constraints, tiny habits framework, cultural considerations, WHO NCD 2030 targets |

### Embedded Sample Guidelines

In addition to these files, `app/core/rag/indexer.py` contains 6 embedded `SAMPLE_GUIDELINES` (shorter summaries of similar topics). Both the embedded samples and directory files are indexed when you run `setup_rag.py`. The directory files provide deeper, more detailed coverage.

## Sources

All guideline content is derived from publicly available WHO publications:

- WHO Fact Sheet: Hypertension (Key Facts) — sodium targets, BP thresholds, prevalence data
- WHO Fact Sheet: Diabetes — diagnostic criteria, HbA1c thresholds, global prevalence
- WHO Fact Sheet: Noncommunicable Diseases — burden statistics, modifiable risk factors, 2030 targets
- WHO Fact Sheet: Healthy Diet — macronutrient recommendations, salt/sugar limits
- WHO Fact Sheet: Physical Activity — 150-300 min/week targets, sedentary behavior guidance
- WHO HEARTS Technical Package — risk-based CVD management framework for primary health care
- WHO/ISH Cardiovascular Risk Charts — 10-year risk stratification by region
- WHO Global Action Plan for NCDs 2013-2030 — voluntary targets for tobacco, BP, obesity, salt, activity
- WHO Social Determinants of Health Framework — structural barriers to healthy behavior
- Africa CDC NCD Strategy — context-specific considerations for sub-Saharan Africa

## How to Add New Guidelines

1. Create a markdown file following the naming convention: `{source}_{condition}_{topic}.md`
   - Example: `who_diabetes_complications.md` or `moh_hypertension_medication.md`
2. Write the content in plain markdown. Use headings (`##`) to separate sections — the chunker splits on headings.
3. Run the indexer:
   ```bash
   cd backend
   python setup_rag.py
   ```
4. The indexer will auto-detect metadata from the filename and report chunk counts.

Supported file formats: `.md` and `.txt`. The file `README.md` is automatically skipped.

## How to Re-Index

```bash
cd backend
python setup_rag.py
```

This will:
1. Clear the existing ChromaDB "guidelines" collection
2. Index the 6 embedded sample guidelines from `indexer.py`
3. Index all `.md` and `.txt` files from this directory
4. Print verification stats (total chunks indexed)

You can also run the indexer module directly:
```bash
cd backend
python -m app.core.rag.indexer
```

## Retrieval at Runtime

When a user asks a health question, the agents call `retrieve_guidelines(query, condition, topic)` which:
1. Embeds the query using SentenceTransformers
2. Searches ChromaDB with cosine similarity + metadata filters
3. Returns the top-k most relevant chunks with confidence scores
4. The corrective RAG critic validates that the agent's response is supported by the retrieved evidence

Metadata filters (`condition`, `topic`) narrow the search space so that a hypertension diet question only retrieves hypertension diet chunks, not diabetes activity chunks.
