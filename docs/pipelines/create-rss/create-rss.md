---
title: "Python Utility: create-rss.py"
category: utility
audience:
- content-architects
- devops-engineers
- engineering-leaders
tags:
  - content-syndication
  - automation-scripts
  - content-pipeline
project: publishing-automation
layer: integration
status: published
summary: Python-based RSS generation engine that filters and transforms
  published HTML content into standards-compliant RSS 2.0 feeds,
  enabling automated release syndication within an enterprise publishing
  pipeline.
---

# Python Utility: create-rss.py

**Parent System:** Publishing Automation (Distribution Layer)

------------------------------------------------------------------------

## 1. Architectural Purpose

`create-rss.py` is a syndication engine designed to generate a
standards-compliant RSS 2.0 feed from published HTML documentation.

Executed during the publishing workflow, the utility identifies content
explicitly marked as "What's New," extracts structured metadata,
normalizes internal links, and assembles a deterministic RSS feed
suitable for external distribution systems.

Rather than serving as a simple feed generator, the script functions as
a controlled **release-notification layer**, transforming structured
documentation artifacts into machine-consumable update signals.

------------------------------------------------------------------------

## 2. Role Within the Publishing Pipeline

The publishing workflow executes the following sequence:

1.  Source content is transformed into HTML.
2.  Validation and normalization utilities execute.
3.  `create-rss.py` scans the output directory.
4.  Eligible "What's New" articles are filtered and processed.
5.  A structured `rss_feed.xml` artifact is generated.

The resulting RSS feed enables:

-   Release announcement syndication
-   External notification systems
-   Subscription-based update tracking
-   Automated aggregation compatibility

This ensures documentation updates are discoverable beyond the static
site itself.

------------------------------------------------------------------------

## 3. Controlled Filtering Strategy

Only HTML files explicitly marked with:

``` html
<meta name="is-what-new" content="1">
```

are included in the feed.

This design ensures:

-   Deterministic inclusion rules
-   Author-controlled feed participation
-   Clear separation between general content and release updates
-   Reduced noise in subscriber feeds

The filtering mechanism prevents accidental publication of non-release
content.

------------------------------------------------------------------------

## 4. Metadata Extraction Model

The utility parses HTML using BeautifulSoup and extracts structured
metadata from `<meta>` tags within the `<head>` element, including:

-   Title
-   Description
-   Category
-   Change date
-   Additional page-level metadata

The `change-date` value is converted into RFC 822 format to comply with
RSS 2.0 specifications.

This guarantees compatibility with feed readers and syndication
platforms.

------------------------------------------------------------------------

## 5. Content Normalization and Link Rewriting

The script identifies the primary content container (`conbody` or
`refbody`) and performs link normalization:

-   Relative internal links are rewritten as absolute URLs.
-   External links (e.g., `target="_blank"`) are preserved.
-   Canonical product and language segments are injected based on
    configuration.

This ensures:

-   Feed-safe HTML
-   Valid absolute links
-   Cross-system portability
-   Consistent URL resolution across environments

------------------------------------------------------------------------

## 6. Deterministic GUID Modeling

Each RSS item includes a `<guid>` value intentionally structured to:

-   Group related updates by category and month
-   Maintain stable identifiers across feed refreshes
-   Prevent duplicate item proliferation in feed readers

This approach supports controlled update grouping and predictable
subscription behavior.

------------------------------------------------------------------------

## 7. Sorting and Feed Assembly

After processing eligible files:

1.  Items are sorted by publication date (ascending).
2.  Channel metadata is constructed using a JSON configuration file.
3.  A final `rss_feed.xml` document is generated with:
    -   Channel metadata
    -   `<lastBuildDate>` injection
    -   Ordered `<item>` blocks
    -   CDATA-wrapped HTML content

The output file is written to the publishing directory as a standalone
distribution artifact.

------------------------------------------------------------------------

## 8. Configuration Model

The script is intentionally decoupled from product identity through an
external JSON configuration file.

Example structure:

``` json
{
  "Title": "Product Documentation - What's New",
  "ProductSectionid": "Release update feed for documentation changes.",
  "ProductSectionKey": "PRODUCT-KEY",
  "Language": "en-us"
}
```

This separation allows the utility to be reused across multiple
repositories and product documentation sets without code modification.

------------------------------------------------------------------------

## 9. Engineering Characteristics

This utility demonstrates:

-   Structured HTML parsing
-   Metadata-driven filtering
-   Deterministic content selection
-   Standards-compliant RSS 2.0 generation
-   URL normalization strategies
-   Configuration decoupling
-   Stable identifier modeling
-   Automated distribution artifact generation

It was designed to operate unattended within an enterprise publishing
pipeline.

------------------------------------------------------------------------

## 10. Strategic Value

`create-rss.py` enables structured documentation updates to function as:

-   Machine-readable release signals
-   Subscription-based notification streams
-   Aggregation-compatible distribution feeds
-   External content integration artifacts

By transforming documentation changes into standardized syndication
output, the utility extends the reach of static documentation into
dynamic update ecosystems.

------------------------------------------------------------------------

## 11. Portfolio Positioning

This utility represents the **distribution layer** of a larger
publishing automation architecture.

Together with validation, metadata normalization, ingestion preparation,
and workflow synchronization systems, it contributes to a fully
automated content lifecycle designed for:

-   Structured publishing
-   Deterministic automation
-   Multi-system integration
-   AI-ready knowledge distribution
