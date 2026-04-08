---
title: Retrieval-Augmented Generation (RAG) Architecture Design Specification
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
  - embeddings
  - prompt-engineering
  - vector-database
  - ai-integration
  - data-modeling
  - content-pipeline
project: portfolio-chatbot
layer: platform
status: published
summary: End-to-end architectural design of a Retrieval-Augmented Generation (RAG) system for a portfolio chatbot, including ingestion pipeline, Markdown parsing, metadata extraction, chunking strategy, embedding generation, FAISS-based vector indexing, hybrid retrieval scoring, MMR diversity selection, cross-encoder reranking, document-aware aggregation, knowledge graph expansion, and LLM-based response generation within a low-infrastructure, static-site-compatible deployment model.
---
<a id="pc-project-overview"></a>
## 1. Project Overview

### 1.1 Objective

This project implements a **Retrieval-Augmented Generation (RAG) system** that enables visitors to interact with a technical portfolio using natural language queries.

The chatbot retrieves relevant information from a corpus of Markdown-based documentation and generates answers grounded in the portfolio’s content.

The system is designed both as:

  - a functional portfolio search assistant
  - a demonstration of modern AI retrieval architecture

### 1.2 Key Goals

The system is designed to:

  - Enable natural language search over portfolio documentation
  - Ground AI responses in existing content
  - Leverage structured metadata contained in Markdown frontmatter
  - Remain compatible with static site hosting
  - Minimize infrastructure complexity and cost
  - Demonstrate advanced retrieval architecture techniques

### 1.3 Architectural Philosophy

The system emphasizes **retrieval quality over model size**.

Rather than relying solely on LLM reasoning, the architecture focuses on improving the relevance and diversity of retrieved context through:

  - hybrid retrieval scoring
  - metadata awareness
  - intent-aware retrieval weighting
  - diversity selection
  - semantic reranking

These techniques improve answer quality while keeping infrastructure lightweight.

<a id="pc-high-level-architecture"></a>
## 2. High-Level Architecture

The system is composed of four major subsystems:

1. Content Source Layer
2. Ingestion Engine
3. Retrieval & AI Layer
4. Frontend Chat Interface

```
                ┌────────────────────────────┐
                │     Markdown Knowledge     │
                │  (Portfolio Documentation) │
                └─────────────┬──────────────┘
                              │
                       Ingestion Engine
                              │
                      Chunk Generation
                              │
                     Embedding Generation
                              │
                     Vector Index (FAISS)
                              │
                     Retrieval Pipeline
                              │
                        LLM Completion
                              │
                        Chat Interface
```

The architecture separates **offline indexing** from **runtime retrieval**.

### Offline Processing

Performed by the ingestion engine:

  - parse Markdown documents
  - extract metadata
  - generate content chunks
  - compute embeddings
  - build the vector index

### Runtime Processing

Performed during a user query:

  - query embedding
  - hybrid retrieval
  - diversity filtering
  - semantic reranking
  - prompt construction
  - LLM response generation

<a id="pc-system-components"></a>
## 3. System Components

<a id="pc-sc-content-source-layer"></a>
### 3.1 Content Source Layer

#### Description

The knowledge corpus consists of Markdown files used by the portfolio website.

Each document contains **YAML frontmatter metadata**.

Example:

```
---
title: create-kb-met Go Utility
type: project
category: tooling
tags:
  - dita
  - automation
  - metadata
date: 2026-03-01
---
```

#### Responsibilities

The content layer provides:

  - Human-readable documentation
  - Structured metadata
  - Knowledge corpus for retrieval

#### Supported Content Types

Examples:

  - Projects
  - Technical Articles
  - Architecture Notes
  - Tool Documentation

<a id="pc-sc-ingestion-engine"></a>
### 3.2 Ingestion Engine

#### Description

The ingestion engine converts Markdown-based portfolio content into structured artifacts used by the retrieval system.

This process runs offline as a Python-based pipeline and is responsible for preparing all data required for runtime retrieval.

The ingestion process is divided into two distinct phases:

  - Phase 1 — Content Processing
  - Phase 2 — Index Construction

This separation ensures a clean boundary between data preparation and vector indexing.

#### Implementation Language

Python

The ingestion pipeline is implemented as a set of Python scripts to align with:

  - embedding model integration
  - FAISS index generation
  - retrieval system compatibility

#### Responsibilities

The ingestion engine performs the following operations:

Phase 1 — Content Processing:

  1. Parse Markdown files
  2. Extract frontmatter metadata
  3. Extract document body content
  4. Generate content chunks using document structure
  5. Assign document-level identifiers
  6. Build a document-level knowledge graph
  7. Write structured JSON artifacts

Phase 2 — Index Construction:

  1. Load chunk data from JSON artifacts
  2. Generate embeddings using a sentence-transformer model
  3. Build a FAISS vector index
  4. Persist the index to disk

#### Chunking Strategy

Documents are chunked using heading-based segmentation.

Each chunk represents a semantically meaningful section of a document.

Chunk structure includes:

  - document_path
  - title
  - content

This structure enables downstream document-aware retrieval.

#### Output Artifacts

The ingestion pipeline produces the following files:

`data/chunks.json`

`data/knowledge_graph.json`

`data/kb_index.faiss`

`chunks.json` contains all text chunks and associated metadata.

`knowledge_graph.json` stores document relationships as an adjacency map.

`kb_index.faiss` contains vector embeddings for similarity search.

#### Execution

The ingestion and indexing pipeline is executed via:

`scripts/rebuild_index.py`

This script performs both:

  - content processing
  - FAISS index generation

<a id="pc-sc-vector-storage"></a>
### 3.3 Vector Storage

The system uses a hybrid storage model combining structured JSON artifacts with a FAISS vector index.

This design separates:

- textual and structural data (JSON)
- vector embeddings (FAISS)

#### Storage Components

The following data artifacts are used at runtime:

**chunks.json**

Contains all chunked content used for retrieval.

Each entry follows this structure:

  - id: optional unique identifier
  - document_path: source document reference
  - title: document or section title
  - content: chunk text

Embeddings are not stored in this file.

**knowledge_graph.json**

Stores document relationships as an adjacency map.

Example structure:

docA → [docB, docC]

This graph is used during retrieval for document-level context expansion.

**kb_index.faiss**

Contains vector embeddings generated from chunk content.

  - Built using FAISS
  - Loaded into memory during runtime
  - Queried using approximate nearest neighbor search

#### Design Rationale

This storage model provides several advantages:

  - avoids duplication of embedding data in JSON
  - improves memory efficiency
  - enables fast similarity search via FAISS
  - supports modular updates to content and index

#### Retrieval Integration

During query execution:

  1. FAISS returns candidate chunk indices
  2. indices are mapped to entries in chunks.json
  3. chunk data is used for scoring, ranking, and grouping
  4. knowledge_graph.json is used for context expansion

#### Capacity Considerations

The system is designed for portfolio-scale datasets.

Typical size:

  - up to several thousand chunks
  - fully in-memory FAISS index

This avoids the need for external vector databases while maintaining fast retrieval performance.

<a id="pc-sc-retrieval-ai-layer"></a>
### 3.4 Retrieval & AI Layer

The Retrieval and AI Layer is responsible for transforming user queries into grounded, context-aware responses using a multi-stage retrieval pipeline.

This system goes beyond basic vector similarity search by incorporating:

- hybrid scoring
- diversity filtering (MMR)
- semantic reranking
- document-aware aggregation
- knowledge graph expansion

These steps significantly improve both **retrieval precision** and **context quality**, enabling more accurate and explainable responses.

#### 3.4.1 Retrieval Pipeline

The runtime pipeline executes the following stages:

  - User Query
  - Query Expansion (rule-based)
  - Query Intent Classification (rule-based)
  - Query Embedding (SentenceTransformers)
  - FAISS Vector Search (top ~30 chunks)
  - Hybrid Scoring (vector + keyword + hierarchy + metadata + intent)
  - MMR Diversity Selection (k ≈ 12)
  - Cross-Encoder Reranking
  - Document-Aware Aggregation
  - Top Documents (top 3)
  - Top Chunks per Document (top 2)
  - Knowledge Graph Expansion (document-level)
  - Prompt Construction
  - LLM Response Generation

#### 3.4.2 Query Expansion

User queries are expanded using rule-based techniques to improve recall.

This step helps bridge vocabulary gaps between:

  - user phrasing
  - technical terminology in documentation

#### 3.4.3 Query Intent Classification

The system performs lightweight, rule-based query intent classification prior to retrieval scoring.

Intent categories:

  - identity — questions about the author (e.g., "Who is Michael Taylor?")
  - experience — questions about career history, roles, and projects
  - technical — questions about system design, architecture, or implementation

Intent is determined using keyword matching against the user query.

This classification influences retrieval behavior by adjusting metadata-based scoring weights.

**Design Rationale**

This approach enables:

  - prioritization of profile-related documents for identity queries
  - improved alignment between query intent and retrieved content
  - better separation between technical and biographical responses

The classifier is intentionally lightweight and deterministic to avoid additional model overhead.

#### 3.4.4 Query Embedding

The expanded query is converted into a vector embedding using:

`sentence-transformers/all-MiniLM-L6-v2`

#### 3.4.5 Vector Retrieval (FAISS)

A FAISS index is used to perform approximate nearest neighbor search.

  - Input: query embedding
  - Output: top ~30 candidate chunks

This stage prioritizes **recall**, returning a broad candidate pool for downstream filtering.

#### 3.4.6 Hybrid Scoring

Each candidate chunk is rescored using a hybrid approach combining:

  - vector similarity (semantic relevance)
  - keyword overlap (lexical match)
  - hierarchy weighting (title relevance)
  - metadata matching (category, tags)
  - intent-aware boosting

Metadata extracted from Markdown frontmatter is actively used during scoring to improve relevance.

Intent-aware boosting dynamically adjusts scoring weights based on the classified query intent, improving alignment between user intent and retrieved content.

This improves performance in cases where:

  - exact terminology matters
  - embeddings alone are insufficient

#### 3.4.7 Diversity Selection (MMR)

Maximal Marginal Relevance (MMR) is applied to reduce redundancy.

  - Input: ~30 candidates
  - Output: ~12 diverse chunks

MMR balances:

  - relevance to the query
  - diversity across sources

This prevents over-representation of a single document or section.

#### 3.4.8 Semantic Reranking

A cross-encoder model is used for final ranking:

`cross-encoder/ms-marco-MiniLM-L-6-v2`

This model evaluates query–chunk pairs directly and produces a more precise relevance ranking than embedding similarity alone.

#### 3.4.9 Document-Aware Aggregation

Unlike naive RAG systems, this implementation performs **document-level grouping**.

Steps:

  1. Group chunks by document_path
  2. Score each document using its highest-ranked chunk
  3. Select top 3 documents
  4. Select top 2 chunks per document

This ensures:

  - better contextual coherence
  - reduced fragmentation
  - stronger alignment with how humans consume documentation

#### 3.4.10 Knowledge Graph Expansion

After document selection, the system expands context using a document-level knowledge graph.

The graph is stored as an adjacency map:

```
{
  "docA": [
    "docB",
    "docC"
  ]
}
```

Expansion behavior:

  - retrieve related documents for selected top documents
  - include additional supporting context when relevant

This enables:

  - cross-document reasoning
  - improved coverage of related concepts

#### 3.4.11 Context Assembly

The final context is constructed from:

  - top-ranked chunks (document-aware selection)
  - graph-expanded documents (when applicable)

The context is structured to:

  - preserve document boundaries
  - maintain logical grouping
  - maximize relevance per token

#### 3.4.12 Response Generation

The final prompt is sent to the language model:

`GPT-4o-mini`

The model generates a response grounded entirely in retrieved context.

This ensures:

  - factual consistency with the knowledge base
  - reduced hallucination risk
  - explainability via source attribution

#### 3.4.13 Metadata Usage

Metadata extracted from Markdown frontmatter is actively used during retrieval scoring.

Metadata fields include:

  - category
  - tags
  - project
  - layer

Metadata contributes to retrieval through:

  - direct matching between query terms and metadata values
  - weighted scoring bonuses for matching categories and tags
  - integration into hybrid scoring alongside vector and keyword signals

This enables:

  - improved relevance for structured queries
  - better alignment between user intent and content type
  - enhanced discoverability of portfolio and profile content

Metadata-aware scoring is further enhanced by query intent classification, allowing the system to prioritize different content types dynamically.

<a id="pc-sc-frontend-chat-interface"></a>
### 3.5 Frontend Chat Interface

#### Description

A lightweight JavaScript chat interface embedded in the portfolio site.

#### Responsibilities

The frontend must:

  - Capture user queries
  - Send requests to API endpoint
  - Display responses
  - Optionally show sources

#### Example UI Features

  - Floating chat button
  - Conversation history
  - Source citations
  - Link to relevant portfolio pages

<a id="pc-security-model"></a>
## 4. Security Model

### API Key Management

LLM API keys must be stored only within the serverless platform.

They must **never appear in client-side code**.

### Access Control

CORS should restrict requests to:

```
portfolio domain
```

<a id="pc-metadata-aware-retrieval"></a>
## 5. Metadata-Aware Retrieval

One of the design goals of the system is to leverage structured metadata present in Markdown frontmatter.

Example metadata:

- title
- type
- category
- tags

This metadata enables **metadata-aware retrieval strategies**, including:

- metadata filtering
- metadata scoring
- hybrid metadata + semantic ranking

Example filter:

- type: project
- tags: automation

This allows the system to restrict search to relevant content classes.

### Planned Capabilities

Future versions of the retrieval engine will support:

  - metadata filter parameters in API requests
  - weighted metadata scoring
  - structured query filtering
  - UI-based filtering options

These features allow the chatbot to behave more like a **semantic search engine** than a simple question-answering system.

<a id="pc-deployment-model"></a>
## 6. Deployment Model

### 6.1 Repository Structure

The system is organized into the following structure:

```
repo-root
│
├── site
│   └── static portfolio output
│
├── api
│   └── serverless endpoint for query handling
│
├── scripts
│   └── ingestion and indexing pipeline
│
├── data
│   └── chunks.json
│   └── knowledge_graph.json
│   └── kb_index.faiss
│
└── docs
    └── architecture and documentation files
```

### 6.2 Ingestion and Indexing

The ingestion pipeline is executed using:

`scripts/rebuild_index.py `

This script performs:

  - content parsing and chunking
  - knowledge graph construction
  - embedding generation
  - FAISS index creation

All generated artifacts are stored in the data directory.

### 6.3 Runtime Environment

At runtime, the system:

  1. Loads the FAISS index into memory
  2. Loads chunks.json for content retrieval
  3. Loads knowledge_graph.json for context expansion

The retrieval pipeline executes within a serverless API layer.

### 6.4 Architecture Characteristics

The deployment model is designed to:

  - avoid external databases
  - minimize infrastructure complexity
  - support static site hosting
  - enable fast cold-start performance

This approach is well-suited for portfolio-scale applications while maintaining production-quality retrieval behavior.

<a id="pc-implementation-phases"></a>
## 7. Implementation Phases

### Phase 1 — Architecture & Design

Define system architecture and data model.

Deliverables:

  - Architecture specification
  - Data schema
  - Chunking strategy

### Phase 2 — Ingestion Engine

Build ingestion and indexing pipeline.

Deliverables:

  - Markdown parser
  - Chunk generation system
  - Knowledge graph construction
  - JSON artifact generation (chunks.json, knowledge_graph.json)
  - FAISS index generation

### Phase 3 — Retrieval API

Implement serverless endpoint.

Deliverables:

  - Query embedding
  - Vector similarity search
  - Context assembly
  - LLM response generation

### Phase 4 — Chat Interface

Build frontend chat component.

Deliverables:

  - Chat UI
  - API integration
  - Response rendering

### Phase 5 — Evaluation & Tuning

Evaluate retrieval quality.

Tasks:

  - Adjust chunk size
  - Improve prompts
  - Tune top-K retrieval

<a id="pc-future-enhancements"></a>
## 8. Future Enhancements

Possible future improvements include:

- Intent confidence scoring
- Metadata filter UI (user-selectable filters)
- Conversation memory
- Knowledge graph visualization
- Adaptive retrieval weighting based on query patterns

<a id="pc-success-criteria"></a>
## 9. Success Criteria

The project will be considered successful if:

- Users can ask questions about portfolio projects
- Responses cite real portfolio content
- The system runs on low-cost infrastructure
- Architecture is clearly documented
- The implementation demonstrates strong engineering practices

