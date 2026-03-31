---
title: AI Ingestion Engine Implementation Plan
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
  - modular-architecture
  - deterministic-processing
project: portfolio-chatbot
layer: data
status: draft
summary: Implementation plan for the AI ingestion engine, defining a modular Python-based pipeline that performs document discovery, frontmatter parsing, heading-based chunking, knowledge graph construction from MkDocs navigation, embedding generation using SentenceTransformers, and FAISS index creation, orchestrated through a deterministic command-line workflow with validation safeguards, CI/CD integration, and strict alignment between chunk data and vector index artifacts.
---
# AI Ingestion Engine Implementation Plan

## 1. Overview

This document defines the implementation structure for the AI Ingestion Engine described in the system architecture.

The ingestion engine converts documentation content into structured knowledge artifacts used by the chatbot retrieval system.

Implementation goals:

* deterministic processing
* modular architecture
* simple execution
* CI/CD compatibility
* maintainability

The ingestion system will be implemented as a Python command-line utility.

---

## 2. Execution Model

The ingestion engine runs as a single command.

Example:

```
python scripts/rebuild_index.py
```

Execution pipeline:

```
Phase 1 — Ingestion
discover documents
        ↓
parse frontmatter
        ↓
chunk documents
        ↓
build knowledge graph
        ↓
write artifacts

Phase 2 — Semantic Indexing
load chunks
        ↓
generate embeddings
        ↓
build FAISS index
```

---

## 3. Repository Structure

The ingestion system will be organized as follows:

```
ai/
   ingestion/
        document_loader.py
        frontmatter_parser.py
        chunker.py
        graph_builder.py
        artifact_writer.py

scripts/
        rebuild_index.py

data/
        chunks.json
        kb_index.faiss
        knowledge_graph.json
```

---

## 4. Component Responsibilities

### 4.1 Document Loader

File:

```
ai/ingestion/document_loader.py
```

Purpose:

Discover Markdown documents within the repository.

Responsibilities:

* scan documentation directory
* identify Markdown files
* return file paths

Example output:

```
[
  "source/architecture/ai-pipeline.md",
  "source/automation/power-automate.md"
]
```

Key function:

```
load_documents(source_directory)
```

---

### 4.2 Frontmatter Parser

File:

```
ai/ingestion/frontmatter_parser.py
```

Purpose:

Extract YAML frontmatter metadata from Markdown files.

Responsibilities:

* detect frontmatter block
* parse YAML metadata
* separate body content

Example output:

```
{
  "metadata": {
    "title": "AI Pipeline Architecture",
    "tags": ["ai", "architecture"]
  },
  "content": "## Overview..."
}
```

Key function:

```
parse_document(file_path)
```

---

### 4.3 Document Chunker

File:

```
ai/ingestion/chunker.py
```

Purpose:

Split documents into semantic sections.

Chunk boundaries are determined by Markdown headings.

Supported headings:

```
## H2
### H3
```

Example chunk:

```
{
  "document_path": "source/architecture/ai-pipeline.md",
  "title": "Overview",
  "content": "The AI pipeline orchestrates..."
}
```
Constraint:

- document_path must remain stable across builds
- no metadata included yet

Key function:

```
chunk_document(parsed_document)
```

Chunk IDs should be deterministic and derived from:

```
document_name + section_name
```

---

### 4.4 Knowledge Graph Builder

File:

```
ai/ingestion/graph_builder.py
```

Purpose:

Construct document relationships derived from the MkDocs navigation structure.

Input file:

```
mkdocs.yml
```

Responsibilities:

* parse navigation tree
* derive relationships between documents
* produce a structure usable by the retrieval systems

### Output Format (Runtime Contract)

The knowledge graph MUST be serialized as an adjacency map:

```
{
"source/architecture/ai-pipeline.md": [
  "source/architecture/ingestion-engine.md"
  ]
}
```

### Notes

- Keys represent `document_path`
- Values represent related documents
- This format is required for retrieval-time expansion

### Important Constraint

Graph expansion operates at the DOCUMENT LEVEL, not chunk level.

Key function:

```
build_graph(nav_structure)
```

---

### 4.5 Embedding & Index Generation

File:

```
scripts/build_semantic_index.py
```

### Purpose:

Generate vector embeddings for document chunks and build the vector index used in retrieval.

### Model

sentence-transformers/all-MiniLM-L6-v2

### Input

```
data/chunks.json
```

Embeddings are generated from:

```
chunk["content"]
```


### Process

- load chunk content from `chunks.json`
- encode all chunks using SentenceTransformers
- normalize embeddings
- build FAISS index using L2 distance
- persist index to disk

### Index Type

```
faiss.IndexFlatL2
```

### Output

```
data/kb_index.faiss
```

### Important Constraints

- Embeddings MUST be normalized (`normalize_embeddings=True`)
- The same model MUST be used at query time
- Index and chunk order MUST remain aligned

### Notes

- Embeddings are NOT stored separately
- FAISS index is the single source of truth for vector search
- This step is executed as a separate script, not part of the core ingestion modules

---

### 4.6 Artifact Writer

File:

```
ai/ingestion/artifact_writer.py
```

Purpose:

Serialize ingestion outputs to disk.

Artifacts written:

```
data/chunks.json  
data/knowledge_graph.json
```

Note:

The FAISS index (`kb_index.faiss`) is NOT written by this component.
It is generated separately during the semantic indexing phase.

Responsibilities:

* JSON serialization
* deterministic output ordering
* file overwrite safety

Key function:

```
write_artifacts()
```

---

## 5. Orchestration Script

File:

```
scripts/rebuild_index.py
```

Purpose:

Orchestrate the full ingestion and indexing pipeline.

Responsibilities:

* invoke ingestion modules (parsing, chunking, graph building)
* write ingestion artifacts
* trigger semantic index generation
* coordinate execution flow
* handle logging

### Execution Flow

The rebuild process consists of two sequential phases:

### Phase 1 — Content Ingestion

```
documents = load_documents()

for doc_path in documents:
metadata, content = parse_frontmatter(doc_path)
doc = Document(...)
chunks.extend(chunk_markdown(doc))

graph = build_graph()

write_all(documents, chunks, graph)
```

Outputs:

```
data/chunks.json
data/knowledge_graph.json
```

---

### Phase 2 — Semantic Indexing

After ingestion artifacts are written, the FAISS index is built by invoking:

```
scripts/build_semantic_index.py
```

This is executed via subprocess:

```
subprocess.run([sys.executable, "scripts/build_semantic_index.py"])
```

Output:

```
data/kb_index.faiss
```

---

### Important Notes

- The FAISS index is built AFTER chunks are generated
- The index depends on `chunks.json` and must always be regenerated when chunks change
- This ensures alignment between:
  - chunk content
  - embedding vectors
  - FAISS index entries

---

### Validation rule:

- Number of vectors in FAISS index MUST equal number of chunks in `chunks.json`

If this condition fails:

- the rebuild process exits with an error
- the index is considered invalid

#### Purpose

This ensures:

- chunk ↔ embedding alignment
- reliable vector search behavior
- protection against partial or corrupted index builds

---

### Final Outcome

A single command:

```
python scripts/rebuild_index.py
```

produces a fully synchronized retrieval system:

* chunks.json
* knowledge_graph.json
* kb_index.faiss

---

## 6. Dependency Requirements

Python packages required:

```
sentence-transformers
faiss-cpu
pyyaml
markdown
```

These should be added to:

```
requirements.txt
```

---

## 7. Logging Strategy

Logging should provide visibility into ingestion progress.

Example:

```
[INFO] Discovering documents
[INFO] Found 32 markdown files
[INFO] Generated 210 chunks
[INFO] Building knowledge graph
[INFO] Building FAISS index
[INFO] Validating index
[INFO] Writing artifacts
```

This helps debugging during CI runs.

---

## 8. Error Handling

The ingestion engine must handle:

* missing frontmatter
* malformed YAML
* empty documents
* navigation mismatches

Errors should not terminate ingestion unless critical.

---

## 9. Performance Expectations

Expected scale:

| Metric    | Target |
| --------- | ------ |
| Documents | <200   |
| Chunks    | <2000  |

Processing time should remain under:

```
30 seconds
```

This is acceptable for CI execution.

---

## 10. CI/CD Integration

The ingestion engine will eventually run as part of the repository's build pipeline.

Example workflow:

```
Git Push
   ↓
Run ingestion engine
   ↓
Update vector index
   ↓
Deploy site
```

This ensures the chatbot index always reflects the latest documentation.

---

## 11. Future Enhancements

Potential improvements include:

- metadata integration
- metadata filtering
- graph-weighted retrieval
- chunk scoring improvements

---

## 12. Summary

The ingestion engine is composed of modular Python components responsible for converting Markdown documentation into structured AI-ready artifacts.

Key outputs:

```
chunks.json  
knowledge_graph.json  
kb_index.faiss
```

These artifacts form the foundation of the chatbot retrieval system.
