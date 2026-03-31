---
title: AI Ingestion Engine Specification
category: architecture
audience:
  - engineering-leaders
  - solution-architects
  - developers
  - devops-engineers
tags:
  - rag
  - embeddings
  - vector-database
  - context-retrieval
  - knowledge-graph
  - data-modeling
  - content-pipeline
  - automation-scripts
  - workflow-orchestration
  - ai-integration
project: portfolio-chatbot
layer: data
status: draft
summary: Detailed specification of the AI ingestion engine responsible for transforming Markdown documentation into structured knowledge artifacts for a RAG-based chatbot, including frontmatter extraction, heading-based chunking, knowledge graph construction from MkDocs navigation, embedding generation using SentenceTransformers, and FAISS index creation for semantic retrieval within a deterministic, CI/CD-compatible pipeline.
---
# AI Ingestion Engine Specification

## 1. Overview

The AI Ingestion Engine is responsible for transforming the documentation platform's Markdown content into structured data artifacts suitable for Retrieval-Augmented Generation (RAG).

The ingestion process converts human-authored documentation into machine-readable knowledge representations used by the portfolio chatbot.

### Objectives

The ingestion engine must:

* Parse Markdown documents from the `source/` directory
* Extract and normalize frontmatter metadata
* Segment documents into semantically meaningful chunks
* Generate embeddings and construct FAISS index for retrieval
* Construct a knowledge graph derived from site navigation
* Produce data artifacts used by the chatbot retrieval system

The ingestion process is deterministic and can be safely executed as part of a CI/CD pipeline.

---

## 2. System Context

The ingestion engine is part of the AI architecture layer.

### Architecture Overview

```
Markdown Content
        │
        ▼
Ingestion Engine
        │
        ├── chunks.json
        │
        ├── knowledge_graph.json
        │
        └── kb_index.faiss
                │
                ▼
          Retrieval Engine
                │
                ▼
            Chatbot API
```

Artifacts are stored in the `data/` directory.

---

## 3. Input Sources

### 3.1 Documentation Content

Location:

```
source/
```

Content format:

* Markdown (`.md`)
* YAML frontmatter
* Structured headings

Example:

```markdown
---
title: Power Automate AI Pipeline
type: article
tags:
  - automation
  - ai
summary: AI-assisted automation workflow
---

# Power Automate AI Pipeline

## Overview

This pipeline orchestrates document processing...

## Architecture

The system consists of three stages...
```

---

### 3.2 Site Navigation

Navigation configuration is defined in:

```
mkdocs.yml
```

Example:

```yaml
nav:
  - Home: index.md
  - Architecture:
      - AI Pipeline: architecture/ai-pipeline.md
      - Ingestion Engine: architecture/ingestion-engine.md
```

This structure is used to generate the knowledge graph.

---

## 4. Processing Pipeline

The ingestion system operates in two phases:

### Phase 1 — Content Ingestion

1. Content Discovery  
2. Frontmatter Extraction  
3. Document Chunking  
4. Knowledge Graph Generation  
5. Artifact Serialization (chunks + graph)  

### Phase 2 — Semantic Indexing

6. Embedding Generation  
7. FAISS Index Construction  

---

## 5. Content Discovery

The ingestion engine scans the documentation directory.

Source directory:

```
source/
```

File types:

```
*.md
```

Output:

```
List of Markdown documents
```

---

## 6. Frontmatter Extraction

Frontmatter metadata is extracted but NOT currently used in retrieval.

Extracted fields:

| Field   | Status        |
| ------- | ------------- |
| title   | used (chunk)  |
| type    | stored (future) |
| tags    | stored (future) |
| summary | stored (future) |

⚠️ Metadata must NOT influence retrieval scoring until fully integrated.

Partial usage may introduce inconsistent ranking behavior.

---

## 7. Document Chunking

Documents are segmented using heading structure.

Supported headings:

H2 (##)
H3 (###)

Each section becomes a chunk.

### Chunk Schema (Current Contract)

```json
{
  "document_path": "string",
  "title": "string",
  "content": "string"
}
```

### Field Definitions

`document_path`: source file path (PRIMARY GROUPING KEY)
`title`: section heading (used for ranking)
`content`: section text

### Critical Constraint

`document_path` MUST be stable and deterministic.

It is used for:

- document grouping
- document-level ranking
- graph expansion

Changing this format will break retrieval behavior.

### Notes

- No metadata is stored in chunks (yet)
- Chunk IDs are NOT required

---

## 8. Knowledge Graph Generation

The knowledge graph is derived from MkDocs navigation.

Source:

mkdocs.yml

### Runtime Format (Official)

```json
{
  "source/architecture/ai-pipeline.md": [
    "source/architecture/ingestion-engine.md"
  ]
}
```

### Description
- Keys = document_path
- Values = related documents

### Purpose

Used during retrieval to expand context AFTER document selection.

### Important Constraint

Graph expansion operates at the DOCUMENT LEVEL, not chunk level.

---

## 9. Embedding Generation

Embeddings are generated using SentenceTransformers.

Model:

sentence-transformers/all-MiniLM-L6-v2

### Notes

- Used for both indexing and query encoding
- Query expansion occurs BEFORE embedding
- Embeddings are stored in FAISS index (not JSON)

### Important Constraint

The same embedding model and normalization settings MUST be used during both indexing and query time.

Any mismatch will result in degraded or invalid similarity scoring.

---

## 10. Generated Artifacts

The ingestion engine produces three primary artifacts.

### chunks.json

Structured chunks used for retrieval.

```
data/chunks.json
```

---

### kb_index.faiss

FAISS vector index containing embeddings.

```
data/kb_index.faiss
```

---

### knowledge_graph.json

Adjacency map for document relationships.

```
data/knowledge_graph.json
```

---

## 11. Repository Layout

The AI system resides in the `ai/` directory.

```
ai/
   ingestion/
       artifact_writer.py
       document_loader.py
       document_model.py
       frontmatter_parser.py
       graph_builder.py
       
   chunking/
       build_chunks.py
       markdown_chunker.py

   retrieval/
       hybrid_search.py

scripts/
   ask_docs.py
   build_semantic_index.py
   content_build.py
   metadata_validator.py
   rebuild_index.py
   search_kb.py
   
data/
   chunks.json
   kb_index.faiss
   knowledge_graph.json
```

---

## 12. CI/CD Integration

The ingestion engine can be executed during CI builds.

Example workflow:

```
Git Push
   │
   ▼
CI Pipeline
   │
   ▼
Run ingestion pipeline (rebuild_index.py)
   │
   ▼
Artifacts + FAISS index generated
   │
   ▼
Deploy site   
```

This ensures the chatbot index remains synchronized with documentation updates.

---

## 13. Future Enhancements

- metadata integration into chunks
- metadata-based filtering
- incremental indexing
- improved graph weighting
- response citations

---

## 14. Implementation Language

The ingestion engine will be implemented in:

Python

This aligns with the existing automation scripts used within the repository.

---

## 15. Summary

The AI Ingestion Engine transforms static documentation into structured knowledge artifacts enabling semantic search and AI-assisted interaction.

Key outputs include:

* chunks.json (document chunks)
* kb_index.faiss (vector index)
* knowledge_graph.json (document relationships)

These artifacts form the foundation of the portfolio chatbot's retrieval system.
