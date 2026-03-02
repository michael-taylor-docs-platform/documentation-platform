# Portfolio Architecture

## 1. Overview

This documentation platform is intentionally designed as a deterministic, enterprise-style documentation pipeline.

It demonstrates:

- Structured source ingestion (DITA XML, Markdown)
- Deterministic transformation layer (Python-based processing)
- Controlled publishing workflow (manual release trigger)
- Static site generation (MkDocs + Material)
- CI/CD automation via GitHub Actions
- AI-assisted transformation and restructuring layer

The platform separates content processing from publishing, mirroring enterprise documentation governance models.

---

## 2. High-Level Architecture

```mermaid
graph TD

    A[Source Content] --> B[Deterministic Transform Layer]
    B --> C[Normalized Markdown Output]
    C --> D[MkDocs Build Engine]
    D --> E[Static Site Artifacts]

    E --> F[Manual Publish Trigger]
    F --> G[GitHub Actions Workflow]
    G --> H[GitHub Pages Deployment]

    subgraph Source Formats
        A1[DITA XML]
        A2[Markdown]
    end

    A1 --> A
    A2 --> A

    subgraph Future Layer
        AI[AI-Assisted Restructuring]
    end

    AI -. optional enhancement .-> B
```