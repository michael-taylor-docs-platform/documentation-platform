---
title: Data Model Specification
category: architecture
audience:
  - engineering-leaders
  - solution-architects
  - developers
  - devops-engineers
tags:
  - rag
  - data-modeling
  - knowledge-graph
  - embeddings
  - vector-database
  - semantic-search
  - context-retrieval
  - hybrid-retrieval
  - ai-integration
  - content-pipeline
project: portfolio-chatbot
layer: data
status: published
summary: Comprehensive data model specification for a RAG-based portfolio chatbot, defining the structure and transformation of content across source documents, parsed document models, chunk representations, metadata schemas, vector embeddings, retrieval signals, query models, and prompt context assembly to support efficient semantic search, hybrid ranking, and LLM-based response generation.
---
<a id="dms-overview"></a>
## 1. Overview

This document defines the **data structures used throughout the RAG system** supporting the portfolio chatbot.

The data model governs how content is:

- Parsed
- Chunked
- Embedded
- Stored
- Retrieved
- Delivered to the AI model

The design emphasizes:

- Structured metadata
- Transparency
- Compatibility with static hosting
- Ease of debugging
- Extensibility

<a id="dms-data-layers"></a>
## 2. Data Model Layers

The system uses four logical data layers.

```
Source Content
    │
    ▼
Document Model
    │
    ▼
Chunk Model
    │
    ▼
Vector Index Model
```

Each layer progressively transforms the data for AI retrieval.

<a id="dms-source-content-model"></a>
## 3. Source Content Model

### 3.1 Description

Source content consists of Markdown documents used by the portfolio website.

Each document contains:

  - YAML frontmatter
  - Markdown body content

### 3.2 Example Document

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
summary: CLI tool that converts SharePoint JSON into DITA metadata files.
---

# Overview

The create-kb-met utility is a command-line tool written in Go...
```

### 3.3 Source Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| title | string | yes | Document title |
| type | string | yes | Content type |
| category | string | optional | Content grouping |
| tags | array[string] | optional | Keyword tags |
| date | date | optional | Publication date |
| summary | string | optional | Short description |

<a id="dms-document-model"></a>
## 4. Document Model

### 4.1 Description

The Document Model represents the parsed structure of a Markdown file.

This model exists **only during ingestion**.

### 4.2 Structure

```
{
  "document_id": "create-kb-met",
  "source_path": "/projects/create-kb-met.md",
  "metadata": {},
  "content": ""
}
```

### 4.3 Fields

| Field | Type | Description |
| --- | --- | --- |
| document_id | string | Unique identifier |
| source_path | string | Location in repository |
| metadata | object | Parsed frontmatter |
| content | string | Markdown body content |

<a id="dms-chunk-model"></a>
## 5. Chunk Data Model

### 5.1 Description

The retrieval system operates on document fragments called "chunks". Each chunk represents a semantically meaningful section of a document that can be retrieved independently during query processing.

Chunks are generated during the ingestion process by splitting Markdown documents along heading boundaries.

Each chunk contains both textual content and metadata used for retrieval and ranking.

### 5.2 Chunk Structure

Each chunk contains the following fields:

  - id: Unique identifier for the chunk.
  - content: The textual content of the chunk.
  - title: The title of the document or section associated with the chunk.
  - document_path: The relative path to the source Markdown document.
  - metadata: Structured metadata extracted from the document frontmatter.
  - embedding: Vector embedding representing the semantic meaning of the chunk.

### 5.3 Example Chunk Object

```
{
  "chunk_id": "create-kb-met-overview",
  "title": "create-kb-met Go Utility",
  "document_path": "/projects/create-kb-met.md",
  "content": "The create-kb-met utility converts SharePoint JSON metadata into DITA-compatible metadata files used in documentation pipelines.",
  "metadata": {
    "type": "project",
    "category": "tooling",
    "tags": "dita, automation, metadata",
    "date": "2026-03-01"
  }
}
```

<a id="dms-metadata-model"></a>
## 6. Metadata Model

### 6.1 Description

Markdown documents used by the portfolio contain YAML frontmatter that provides structured metadata describing the document.

This metadata is extracted during ingestion and stored alongside each chunk.

Metadata enables structured filtering and ranking during retrieval.

### 6.2 Common Metadata Fields

| Field | Type | Description |
| --- | --- | --- |
| title | string | Human-readable title of the document. |
| type | string | Document classification such as: project article architecture tool |
| category | string | Functional category grouping similar documents. |
| tags | array[string] | List of descriptive keywords associated with the document. |
| date | date | Publication date of the document. |

<a id="dms-retrieval-signals"></a>
## 7. Retrieval Signals

### 7.1 Description

The retrieval engine uses multiple signals when ranking candidate chunks.

These signals allow the system to improve relevance beyond simple vector similarity.

### 7.2 Vector Similarity

Semantic similarity between the user query embedding and the chunk embedding.

### 7.3 Keyword Matching

Semantic similarity between the user query embedding and the chunk embedding.

### 7.4 Hierarchy Signals

Structural signals derived from document titles and headings.

These signals help prioritize content that appears in higher-level sections of a document.

### 7.5 Metadata Signals (Planned)

Future versions of the system will incorporate metadata signals into ranking.

Examples include:

  - type matching
  - tag matching
  - category matching

These signals will allow the retrieval system to incorporate structured document information into relevance scoring.

<a id="dms-vector-index-model"></a>
## 8. Vector Index Model

### 8.1 Description

Chunk embeddings are stored in a FAISS vector index to support efficient similarity search.

The vector index stores embeddings for each chunk and enables nearest-neighbor retrieval based on query embeddings.

### 8.2 Index Structure

The index contains:

  - embedding vectors
  - chunk identifiers

When a query is executed, the retrieval engine returns the identifiers of the most similar chunks.

These identifiers are then used to retrieve the full chunk objects from the corpus data.

<a id="dms-metadata-filters"></a>
## 9. Metadata Filtering

Metadata filters allow the retrieval engine to restrict candidate chunks based on structured document attributes.

Example Filters

- type = project
- tags include automation
- category = tooling

Metadata filters may be provided as parameters in API requests.

These filters allow the chatbot to behave more like a semantic search engine over the portfolio content.

<a id="dms-query-model"></a>
## 10. Query Model

### 10.1 Description

The Query Model represents the structure of a user query as it moves through the retrieval pipeline.

It captures both the original user input and any derived representations used during processing.

### 8.2 Fields

| Field | Type | Description |
| --- | --- | --- |
| query_text | string | Identifier of the retrieved chunk. |
| expanded_query | string | A modified version of the query generated during query expansion to improve retrieval recall. |
| query_embedding | string | The vector embedding generated from the expanded query. |
| metadata_filters | number | Optional structured filters applied to restrict retrieval based on metadata. |

### 8.3 Example

```
{
  "query_text: "How does validation work?",
  "expanded_query": "validation system process automated checking pipeline",
  "query_embedding": "[0.012, -0.221, ...]",
  "metadata_filters": "type: pipeline"  
}
```

<a id="dms-retrieval-result-model"></a>
## 11. Retrieval Result Model

### 11.1 Description

The Retrieval Result Model represents candidate chunks returned during the retrieval process along with their associated ranking signals.

Each result includes multiple scores used in hybrid ranking and reranking.

### 11.2 Fields

| Field | Type | Description |
| --- | --- | --- |
| chunk_id | string | Identifier of the retrieved chunk. |
| content | string | Text content of the chunk. |
| document_path | string | Source document location. |
| vector_score | number | Score derived from embedding similarity. |
| keyword_score | number | Score based on keyword overlap with the query. |
| hierarchy_score | number | Score derived from document structure and headings. |
| hybrid_score | number | Combined score used for initial ranking. |
| rerank_score | number | Score assigned during semantic reranking. |

### 11.3 Example

```
{
  "results": [
    {
      "chunk_id": "validation-overview",
      "vector_score": 0.33,
      "keyword_score": 4.0,
      "hierarchy_score": 4.0,
      "hybrid_score": 0.47,
      "rerank_score": 0.82
    }
  ]
}
```

<a id="dms-ai-prompt-context-model"></a>
## 12. AI Prompt Context Model

### 12.1 Description

The AI Prompt Context Model defines how retrieved chunks are assembled and passed to the language model.

The goal is to provide structured, relevant context that enables accurate and grounded responses.

### 12.2 Structure

The prompt context consists of:

  - user query
  - system instructions
  - retrieved content blocks

Each content block includes:

  - title
  - document path
  - chunk content

### 12.3 Example Context Structure

```
User Query:
How does validation work?

Context:

[Document: elixir-automatic-file-validation.md]
Title: Validation Pipeline Overview
Content:
The validation pipeline ensures that all documentation meets structural and metadata requirements...

[Document: file-validator.md]
Title: Validation Checks
Content:
The system validates filenames, identifiers, and metadata attributes...
```

This structured format helps the model generate responses grounded in source material.

<a id="dms-future-data-model-extensions"></a>
## 13. Future Data Model Extensions

The data model is designed to support future enhancements without requiring major restructuring.

Planned extensions include:

- metadata-based filtering fields
- additional ranking signals
- user interaction history
- query analytics data
- feedback scoring for retrieved results

These extensions will support improvements in retrieval accuracy, personalization, and system observability.

<a id="dms-design-principals"></a>
## 14. Design Principles

The data model follows several key principles:

### Simplicity

The model should remain easy to understand and implement.

### Extensibility

New fields and capabilities should be added without breaking existing structures.

### Retrieval Efficiency

The model should support fast lookup and scoring operations.

### Separation of Concerns

Embedding storage, metadata, and content should remain logically distinct.

### Alignment with Retrieval Pipeline

The data model should directly support the needs of the retrieval and ranking system.

