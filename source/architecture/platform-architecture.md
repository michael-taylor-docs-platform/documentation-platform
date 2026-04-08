---
title: Portfolio Architecture
category: architecture
audience:
  - hiring-managers
  - engineering-leaders
  - content-architects
  - devops-engineers
tags:
  - documentation-platform
  - dita
  - markdown
  - mkdocs
  - ci-cd
  - content-pipeline
  - ai-integration
  - content-governance
  - file-validation
project: portfolio-platform
layer: platform
status: published
summary: End-to-end deterministic documentation platform demonstrating structured ingestion, metadata governance enforcement, full-repository validation gates, CI/CD automation, and controlled manual promotion within a static site publishing architecture.
---

# Portfolio Architecture

## 1. Overview

This documentation platform is intentionally designed as a deterministic, governance-enforced documentation system modeled after enterprise publishing infrastructure.

It demonstrates:

- Structured source ingestion (DITA XML, Markdown)
- Deterministic transformation and normalization layer (Python-based processing)
- Enforced metadata governance (schema + taxonomy validation)
- Full-repository validation gates at build time
- CI/CD automation via GitHub Actions
- Strict separation of build and manual publish
- Static site generation (MkDocs + Material)
- AI-assisted transformation and restructuring layer

The platform separates content processing, validation, and publishing into distinct layers, mirroring enterprise documentation governance models where structural integrity is enforced before release.

The platform architecture reflects the operational requirements typical in cybersecurity product organizations, where documentation must support controlled releases, governance validation, and secure publishing workflows.

## 2. High-Level Architecture

```mermaid
flowchart LR

subgraph Content Sources
A[DITA XML Content]
B[Markdown Content]
end

subgraph Processing Layer
C[content_build.py<br>Transform & Normalize]
D[Metadata Governance<br>taxonomy.yaml + validator]
end

subgraph CI/CD Layer
E[GitHub Actions Build Pipeline]
F[Validation + Content Assembly]
end

subgraph Publishing Layer
G[MkDocs Static Site Generator]
H[GitHub Pages Deployment]
end

subgraph AI / Knowledge Layer
I[Metadata Extraction]
J[Vector Database Ingestion]
end

A --> C
B --> C
C --> D
D --> E
E --> F
F --> G
G --> H
H --> I
I --> J
```

## 3. RAG Documentation Architecture

```mermaid
flowchart TD

    A[Documentation Repository<br>/docs Markdown Files]

    B[Document Loader]
    C[Frontmatter Parser]
    D[Markdown Chunker]
    E[Knowledge Graph Builder]
    F[Artifact Writer]

    G[data/documents.json]
    H[data/chunks.json]
    I[data/knowledge_graph.json]

    J[Embedding Generator]
    K[Vector Index]

    L[Hybrid Retriever]

    M[Chatbot API<br>FastAPI]

    N[Portfolio Website]
    O[Chat Interface]

    P[LLM Response Generation]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F

    F --> G
    F --> H
    F --> I

    H --> J
    J --> K

    K --> L
    I --> L

    L --> M

    N --> O
    O --> M

    M --> L
    M --> P
    P --> O
```

### 4. AI Retrieval Pipeline

```mermaid
flowchart TD

    A[User Question]

    B[Chatbot API]

    C[Query Embedding Generator]

    D[Vector Similarity Search]

    E[Top Candidate Chunks]

    F[Knowledge Graph Expansion]

    G[Context Assembler]

    H[Prompt Builder]

    I[LLM Response Generation]

    J[Final Answer]

    A --> B
    B --> C
    C --> D
    D --> E

    E --> F

    F --> G
    E --> G

    G --> H
    H --> I
    I --> J
```