---
title: 'Python Utility: externalLinkCheck.py'
category: utility
audience:
  - content-architects
  - devops-engineers
  - engineering-leaders
tags:
  - automation-scripts
  - reference-processing
  - structured-content
  - content-governance
project: external-link-validation
layer: integration
status: published
summary: Resilient Python-based link validation engine that scans XML content repositories for external references and validates them using layered HTTP checks, JavaScript-aware browser rendering, anti-bot handling, and CI-integrated reporting.
---

# Python Utility: externalLinkCheck.py

**Parent Document:** `Workflow: external-link-check.yml`

------------------------------------------------------------------------

## 1. High-Level Overview & Purpose

`externalLinkCheck.py` is a production-grade Python validation engine
designed to identify broken external links within large XML-based
knowledge base repositories.

The utility was architected to operate reliably within CI/CD
environments where simple HTTP status checks are insufficient due to:

-   JavaScript-heavy sites (Single Page Applications)
-   Soft 404 responses
-   Cloudflare and anti-bot challenges
-   Rate limiting (`429`)
-   HTTP/2 protocol edge cases

Rather than relying on naive link checking, the system implements a
multi-layered validation strategy that progressively escalates
validation complexity only when required. This approach minimizes false
positives while maintaining deterministic CI behavior.

The utility produces structured JSON output for automation pipelines and
exits with a non-zero status code when broken links are detected,
enabling enforcement within GitHub Actions workflows.

------------------------------------------------------------------------

## 2. Core Responsibilities

The utility performs six primary responsibilities:

1.  Recursive XML discovery
2.  External link extraction
3.  Layered HTTP validation with retry logic
4.  JavaScript-aware browser validation fallback
5.  Exception list governance
6.  CI-compatible reporting and exit signaling

------------------------------------------------------------------------

## 3. Execution Flow

### Phase 1: XML File Discovery

The `find_xml_files()` function:

-   Recursively scans the `en-us` content directory
-   Excludes configurable directories (e.g., `ExternalContent`)
-   Produces a filtered list of XML files

------------------------------------------------------------------------

### Phase 2: External Link Extraction

The `process_xrefs()` function:

-   Parses XML using `lxml`
-   Identifies `<xref scope="external">` elements
-   Extracts:
    -   `href`
    -   Link text
    -   Source line number
-   Skips `mailto:` links
-   Tracks non-HTTP protocols separately

------------------------------------------------------------------------

## 4. Multi-Layer Validation Strategy

### Layer 1: Lightweight HTTP Validation

The `check_link_with_retries()` function:

1.  Attempts `requests.head()` for efficiency
2.  Falls back to `requests.get()` if needed
3.  Handles:
    -   `429 Too Many Requests`
    -   `Retry-After` headers
    -   Exponential backoff
    -   Timeouts

------------------------------------------------------------------------

### Layer 2: JavaScript-Aware Browser Validation

If HTTP validation returns a 404 or times out, the script escalates to a
Playwright-based headless browser validation:

-   Launches Chromium in headless mode
-   Waits for `domcontentloaded`
-   Evaluates rendered page state
-   Checks content patterns for false 404 detection

------------------------------------------------------------------------

### Layer 3: Anti-Bot & Cloudflare Handling

The utility detects Cloudflare interstitial pages:

-   Identifies "Just a moment..." challenge titles
-   Waits for title change
-   Differentiates between successful challenge resolution and block
    pages

------------------------------------------------------------------------

### Layer 4: HTTP/2 Protocol Fallback

For `ERR_HTTP2_PROTOCOL_ERROR` cases:

-   Creates a secondary "human-like" browser context
-   Applies realistic `User-Agent`
-   Uses standard viewport dimensions
-   Retries validation

------------------------------------------------------------------------

## 5. Resource Lifecycle Management

To prevent instability during large validation runs:

-   A page refresh interval recreates the Playwright page after a
    configurable number of links.
-   Browser contexts are explicitly closed after processing.
-   The Playwright runtime is initialized once for efficiency.

------------------------------------------------------------------------

## 6. Exception Governance

The script supports an `externalLinkExceptions.txt` file:

-   Maintains a curated list of known acceptable URLs
-   Filters them out of final reporting

------------------------------------------------------------------------

## 7. Output Artifacts

### `brokenLinks.json`

Structured report containing:

-   Filename
-   Link URL
-   Link text
-   HTTP status or error string
-   Source line number

### `otherProtocols.log`

Logs non-HTTP(S) links for manual review.

------------------------------------------------------------------------

## 8. CI/CD Integration Design

If broken links remain after exception filtering:

``` python
sys.exit(1)
```

This intentional non-zero exit code:

-   Fails the GitHub Actions step
-   Triggers downstream notifications
-   Enforces governance at the pipeline level

If no broken links are detected:

-   Exit code `0` is returned
-   Workflow completes successfully

------------------------------------------------------------------------

## 9. Architectural Characteristics

This utility demonstrates:

-   Defensive programming practices
-   Escalation-based validation strategy
-   False-positive mitigation design
-   Browser automation integration
-   Network-aware retry logic
-   Production-grade CI behavior modeling

------------------------------------------------------------------------

## 10. Portfolio Positioning

This utility is part of the **external-link-validation** system, forming
an automated governance framework ensuring external reference integrity
across enterprise knowledge repositories.
