---
title: API Contract Specification
category: architecture
audience:
  - engineering-leaders
  - solution-architects
  - developers
  - devops-engineers
tags:
  - rag
  - semantic-search
  - context-retrieval
  - hybrid-retrieval
  - knowledge-graph
  - llm-orchestration
  - api-integration
  - ai-integration
  - data-modeling
  - response-handling
project: portfolio-chatbot
layer: integration
status: published
summary: Specification of the API contract for a RAG-based portfolio chatbot, defining the POST /chat endpoint, request and response schemas, and the underlying multi-stage retrieval pipeline including query expansion, embedding generation, FAISS-based vector search, hybrid scoring, MMR diversity selection, cross-encoder reranking, document-aware aggregation, knowledge graph expansion, and LLM-driven response generation with source attribution.
---
<a id="acs-overview"></a>
## 1. Overview

This document defines the API contract for the portfolio chatbot system. The API provides a query interface over a structured documentation corpus using a multi-stage retrieval and generation pipeline.

The system implements a **hybrid Retrieval-Augmented Generation (RAG)** architecture with:

- Vector similarity search (FAISS)
- Keyword and hierarchy scoring
- Hybrid score fusion
- MMR-based diversity selection
- Cross-encoder semantic reranking
- Document-aware result selection
- Knowledge graph expansion
- LLM-based answer generation

<a id="acs-high-level-flow"></a>
## 2. High-Level Flow

User Query

→ Query Expansion

→ Query Intent Classification

→ Embedding Generation

→ Vector Search (FAISS)

→ Hybrid Scoring (vector + keyword + hierarchy + metadata + intent)

→ MMR Diversity Selection

→ Cross-Encoder Reranking

→ Document-Aware Selection

→ Knowledge Graph Expansion

→ Prompt Construction

→ LLM Response Generation

<a id="acs-endpoint-definition"></a>
## 3. Endpoint Definition

### 3.1 Endpoint

```
POST /chat
```

### 3.2 Description

Processes a user query and returns a grounded answer based on the documentation corpus.

<a id="acs-request-model"></a>
## 4. Request Model

### 4.1 Request Body

```
{
  "query": "string"
}
```

### 4.2 Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| query | string | yes | Natural language user query |

<a id="acs-response-model"></a>
## 5. Response Model

### 5.1 Response Body

```
{
  "answer": "string",
  "sources": [
    "string"
  ]
}
```

### 5.2 Response Fields

| Field | Type | Description |
| --- | --- | --- |
| answer | string | Generated response from the LLM |
| sources | array | List of unique document paths used to construct the answer |

<a id="acs-retrieval-workflow"></a>
## 6. Retrieval Pipeline Details

### 6.1 Query Expansion

The system expands the input query using a rule-based synonym map.

Example:

```
"metadata pipeline"
→ "metadata schema frontmatter pipeline workflow automation"
```

The expanded query is used for embedding generation.

### 6.2 Query Intent Classification

The system performs lightweight, rule-based query intent classification prior to retrieval scoring.

Supported intents:

  - identity — questions about the author (e.g., "Who is Michael Taylor?")
  - experience — questions about career history and projects
  - technical — questions about system architecture, pipelines, and implementation

Intent classification is based on keyword matching within the query.

**Purpose**

Intent is used to dynamically adjust retrieval scoring, improving alignment between query intent and selected content.

This enables:

  - prioritization of profile content for identity queries
  - stronger weighting of experience-related documents for career queries
  - emphasis on technical documentation for system-related questions

### 6.3 Embedding Generation

  - Model:
  - Input: expanded query
  - Output: normalized embedding vector

### 6.4 Vector Search

  - Index: FAISS ()
  - Retrieval size: top 30 candidates

### 6.5 Hybrid Scoring

Each candidate chunk is scored using:

  - Vector similarity score
  - Keyword match score
  - Hierarchy (title) score
  - Metadata match score (category, tags)
  - Intent-aware scoring adjustments

**Score Fusion**

Scoring is performed using a weighted hybrid model combining semantic, lexical, structural, and metadata signals.

Weights may be dynamically adjusted based on query intent.

### 6.6 MMR Diversity Selection

Maximal Marginal Relevance (MMR) is applied to reduce redundancy and improve diversity.

  - Input: top hybrid-ranked candidates
  - Output: diversified subset (k = 12)

### 6.7 Semantic Reranking

  - Model:
  - Method: query–chunk pair scoring
  - Output: reranked candidates by semantic relevance

### 6.8 Document-Aware Selection

Chunks are grouped by `document_path`.

Selection strategy:

  1. Rank documents by highest-scoring chunk
  2. Select top 3 documents
  3. Select top 2 chunks per document

### 6.9 Knowledge Graph Expansion

A document-level graph is used to identify related documents.

  - Source:
  - Structure: adjacency list (document → related documents)

Additional chunks from related documents may be appended to the result set.

<a id="acs-data-model"></a>
## 7. Data Model (As Used by API)

### Chunk Structure

```
{
  "document_path": "string",
  "title": "string",
  "content": "string",
  "metadata": {
    "category": "string",
    "tags": ["string"],
    "project": "string",
    "layer": "string"
  }
}
```

### Notes

  - Metadata (frontmatter) is
  - Retrieval operates only on:
    - content (semantic similarity)
    - title (hierarchy scoring)
    - metadata (category, tags, project, layer)
    - intent (dynamic scoring adjustment)

<a id="acs-prompt-construction"></a>
## 8. Prompt Construction

The system constructs a structured prompt using retrieved chunks.

Prompt construction is influenced by query intent, which guides response style:

- identity → concise summary of the individual
- experience → emphasis on roles, projects, and career history
- technical → detailed explanation of systems and architecture

### Format

```
DOCUMENT: <document_path>
SECTION: <title>

<content>
```

Multiple sections are concatenated to form the context.

### Prompt Rules

  - Use only provided documentation
  - Do not hallucinate information
  - Combine information across sections when necessary
  - Prefer explicit grounding in source content

<a id="acs-llm-configuration"></a>
## 9. LLM Configuration

1. Provider: OpenAI
2. Model:
3. Temperature:

<a id="acs-output-behavior"></a>
## 10. Output Behavior

### Answer Generation

The LLM produces a natural language response based solely on retrieved context.

### Source Attribution

Sources are derived from:

```
r["document_path"]
```

Returned as a deduplicated list.

<a id="acs-limitations"></a>
## 11. Limitations (Current State)

1. No structured citation linking to specific chunks
2. No scoring transparency in API response
3. Limited intent classification (rule-based only)
4. Knowledge graph expansion is document-level only

<a id="acs-future-api-extensions"></a>
## 12. Future Extensions

1. Metadata-aware filtering and scoring
2. Structured citation references (chunk-level)
3. Debug/trace output (scores, ranking stages)
4. Streaming responses
5. API parameterization (top-k, filters)

