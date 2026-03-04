---
title: 'Go Utility: createMET.go'
category: utility
audience:
- content-architects
- devops-engineers
- engineering-leaders
tags:
- metadata-modeling
- structured-content
- lifecycle-management
- automation-scripts
project: ai-ingestion-pipeline
layer: integration
status: published
summary: Go-based metadata enrichment engine that generates structured
  .MET files from Markdown content, product hierarchy data, and
  navigation models to prepare content packages for vector database
  ingestion within an AI-driven knowledge system.
---

# Go Utility: createMET.go

**Parent System:** AI Ingestion Pipeline (Vector Database Preparation
Layer)

------------------------------------------------------------------------

## 1. Architectural Purpose

`createMET.go` is a metadata enrichment and normalization engine written
in Go.

It operates at the final stage of the publishing workflow and prepares
structured content packages for ingestion into a vector database--backed
AI knowledge system.

Rather than simply generating metadata files, the utility performs
**multi-source aggregation, hierarchical resolution, and relationship
extraction** to produce ingestion-ready `.MET` files.

These files serve as structured metadata envelopes that accompany
converted Markdown content before submission to the AI ingestion engine.

This utility forms a critical bridge between:

-   Human-authored Markdown content
-   Product hierarchy and navigation models
-   Structured metadata requirements
-   AI vector ingestion systems

------------------------------------------------------------------------

## 2. Role Within the AI Ingestion Pipeline

The ingestion pipeline follows this high-level flow:

1.  Source content converted to Markdown
2.  Publishing workflow executes
3.  `createMET.go` generates enriched `.MET` metadata files
4.  Markdown + `.MET` pairs are packaged
5.  Package is transmitted to the vector ingestion engine

The `.MET` file ensures that each content artifact is accompanied by:

-   Canonical product identity
-   Breadcrumb hierarchy
-   Structured metadata
-   Internal link relationships
-   Last-modified timestamps
-   Content classification data

This guarantees that downstream embedding and indexing systems receive
deterministic, normalized metadata alongside the text body.

------------------------------------------------------------------------

## 3. Multi-Source Metadata Aggregation Strategy

For each Markdown file discovered, the utility aggregates metadata from
four independent sources:

### 1. YAML Front Matter

Extracts: - Title - Description - Version - Other page-level metadata

### 2. `publish.json`

Primary product hierarchy model containing: - Product structure -
Navigation tree - File path mapping - Last modified timestamps

### 3. `subproduct.json` (Optional)

Provides deeper, nested breadcrumb resolution for granular product
sections.

### 4. Markdown Body

Parses and extracts: - Internal links - External references -
Relationship graph data

By combining these sources, the utility constructs a unified metadata
representation.

------------------------------------------------------------------------

## 4. Breadcrumb Resolution Strategy

Breadcrumb generation follows a deterministic precedence model:

1.  **Sub-product search (highest specificity)**
2.  **Primary product search (fallback)**
3.  **Default root breadcrumb (minimal fallback)**

The search logic performs recursive traversal through nested JSON
hierarchy structures, matching file paths to product sections.

This ensures:

-   Accurate hierarchical context
-   Stable navigation metadata
-   Proper vector indexing context
-   Reduced ambiguity during AI retrieval

------------------------------------------------------------------------

## 5. Internal Link Extraction

The utility parses Markdown using a structured regular expression to
extract:

-   Link text
-   Destination URL

Extracted links are stored as structured entries in the `.MET` output,
enabling:

-   Relationship-aware indexing
-   Graph enrichment
-   Context expansion during retrieval
-   Link-based relevance scoring in downstream AI systems

------------------------------------------------------------------------

## 6. Output Structure

For each Markdown file, a corresponding `.MET` file is generated
containing:

-   Title
-   Canonical URL
-   Breadcrumb hierarchy
-   Product and sub-product identity
-   Language
-   Version
-   Last updated timestamp
-   Internal link relationships
-   Content type classification

The output is serialized as structured JSON and written to the
configured output directory.

------------------------------------------------------------------------

## 7. Command-Line Interface

Required flags:

-   `-mdPath` --- Directory containing Markdown files
-   `-jsonPath` --- Path to primary `publish.json`
-   `-outputPath` --- Output directory for `.MET` files

Optional flag:

-   `-subproductJSON` --- Path to granular hierarchy model

Example:

``` bash
go run createMET.go   -mdPath "./markdown_articles"   -jsonPath "./data/publish.json"   -subproductJSON "./data/subproduct.json"   -outputPath "./output/met_files"
```

------------------------------------------------------------------------

## 8. Engineering Characteristics

This utility demonstrates:

-   Recursive hierarchy traversal
-   Structured JSON modeling
-   Deterministic metadata normalization
-   Cross-source aggregation
-   Clean separation of concerns
-   Defensive file I/O handling
-   Explicit failure handling for missing critical inputs

It was engineered to operate reliably in automated publishing pipelines
without manual oversight.

------------------------------------------------------------------------

## 9. Strategic Value

`createMET.go` transforms static Markdown content into structured,
ingestion-ready artifacts suitable for:

-   Vector database indexing
-   Retrieval-Augmented Generation (RAG) systems
-   AI-driven search
-   Knowledge graph enrichment
-   Context-aware content retrieval

By enforcing consistent metadata modeling prior to ingestion, it reduces
downstream ambiguity and improves retrieval accuracy in AI systems.

------------------------------------------------------------------------

## 10. Portfolio Positioning

This utility is part of the **ai-ingestion-pipeline** project and
represents the metadata enrichment layer of an enterprise-scale content
lifecycle system.

Together with validation, governance, and publishing automation
components, it contributes to a fully automated structured content
pipeline designed for AI-native knowledge systems.

------------------------------------------------------------------------

## 11. Appendix: Sample `.MET` File

Below is an example of a `.MET` file generated by the `createMET.go` utility. This JSON output demonstrates how the aggregated metadata is structured.

```json
{
  "Title": "How to Configure Enterprise Security Platform",
  "Link": "/enterprise-security-platform/get-started/configuring-enterprise-security-platform.html",
  "Breadcrumbs": [
    {
      "Title": "Enterprise Security Platform",
      "URL": "/enterprise-security-platform.html"
    },
    {
      "Title": "Getting Started",
      "URL": "/enterprise-security-platform/get-started.html"
    },
    {
      "Title": "Configuring Enterprise Security Platform",
      "URL": "/enterprise-security-platform/get-started/configuring-enterprise-security-platform.html"
    }
  ],
  "Language": "en-us",
  "Product": "Enterprise Security Platform",
  "SubProduct": "Getting Started",
  "ConsoleURL": "https://example.console.url",
  "ContentType": "Article",
  "LastUpdated": "2023-10-27T10:00:00Z",
  "Version": "14.0",
  "InternalLinks": [
    {
      "Text": "product documentation",
      "URL": "/enterprise-security-platform/docs/product-guide.html"
    },
    {
      "Text": "troubleshooting guide",
      "URL": "/enterprise-security-platform/support/troubleshooting.html"
    }
  ]
}
```
