---
title: Standalone Guide Reference Processor
category: automation
audience:
  - content-architects
  - engineering-leaders
  - devops-engineers
tags:
  - dita
  - reuse
  - keydefs
  - conrefs
  - cross-references
  - xml-processing
  - automation
  - ci-cd
summary: A DITA processing utility that enables authors to generate production-ready standalone guides by injecting required key definitions, classifying cross-references, and rewriting unsafe project-level links during CI/CD execution.
status: published
---

# Standalone Guide Reference Processor

## 1. Overview

The Standalone Guide Reference Processor was developed to enable authors to create concise, focused standalone guides without needing to remap variables or manually resolve broken cross-references.

Authors can define a custom submap containing only the topics required for a specific deliverable. The script then enhances the standard publishing workflow by automatically:

- Preserving variable resolution through key definition injection
- Rewriting cross-project references that fall outside the selected subset
- Normalizing anchors for correct HTML rendering
- Ensuring environment-aware link generation (staging or production)

This enhancement allows standalone guides to be generated directly from existing content ecosystems without introducing manual correction steps.

---

## 2. Problem Statement

Within large DITA-based documentation systems:

- Topics frequently reference content outside a given subset
- Key definitions are centralized in primary project maps
- Cross-project links are resolved at full-build time
- Variables depend on global key definitions

When authors attempt to generate a smaller, focused guide by creating a submap:

- References to external topics break
- Variables fail to resolve
- Anchors may not map correctly in HTML output
- Manual link remediation becomes necessary

This creates friction, discourages modular reuse, and introduces publishing risk.

---

## 3. Purpose

This script enhances the existing publishing workflow by enabling:

1. Author-defined submaps for targeted standalone guides
2. Automatic injection of required `<keydef>` elements from the main project map
3. Intelligent classification of cross-references
4. Controlled rewriting of references outside the selected subset
5. Preservation of XML structure and DOCTYPE integrity
6. Deterministic execution within CI/CD environments

The result is a self-contained, production-ready standalone guide that:

- Maintains variable resolution
- Prevents broken cross-references
- Requires no manual post-processing
- Integrates seamlessly into the standard publishing pipeline

---

## 4. Execution Parameters

The script requires four command-line arguments:

    python standaloneRef.py <standaloneProject.ditamap> <mainProjectMap> <OnlineHelpPublicationLocation> <productionOrStaging>

### 5. Arguments

  -----------------------------------------------------------------------
  Parameter                          Description
  ---------------------------------- ------------------------------------
  standaloneProject.ditamap          The DITAMAP representing the
                                     extracted standalone guide

  mainProjectMap                     The primary project map containing
                                     global key definitions

  OnlineHelpPublicationLocation      Publication identifier used in URL
                                     generation

  productionOrStaging                Environment selector (`production`
                                     or `staging`)
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 6. Environment-Aware URL Handling

The script dynamically determines the base URL:

Production: https://docs.trendmicro.com/en-us/documentation/article

Staging:
https://servicecentral-stg.powerappsportals.com/en-us/documentation/article

Final base URL format:

    {baseURL}/{publication-location}-

This ensures correct reference rewriting depending on deployment target.

------------------------------------------------------------------------

## 7. High-Level Processing Flow

1.  Parse Standalone DITAMAP
2.  Collect Referenced Topics
3.  Extract keydefs from Main Project Map
4.  Append keydefs to Standalone Map
5.  Process Referenced Files
6.  Detect xrefs and conrefs
7.  Rewrite Internal Project References
8.  Write Modified XML Files

------------------------------------------------------------------------

## 8. Reference Classification Logic

Each `xref` is classified into one of four scopes:

  Scope             Condition
  ----------------- -------------------------------------
  sameFile          Anchor-only references (#section)
  external          Absolute URLs (http, https, www)
  internal          Referenced within standalone scope
  internalProject   Referenced outside standalone scope

Only `internalProject` references are rewritten.

------------------------------------------------------------------------

## 9. Internal Project Reference Rewriting

When an `xref` is classified as `internalProject`:

1.  The referenced topic's `<title>` is extracted.
2.  The `outputclass` attribute is retrieved.
3.  A new external URL is constructed.
4.  Anchor formatting is normalized (`/` → `__`).
5.  The `xref` is rewritten:
    -   `href` updated
    -   `format="html"`
    -   `scope="external"`
    -   Missing link text replaced with topic title

This ensures proper behavior in HTML-rendered standalone output.

------------------------------------------------------------------------

## 10. Key Definition Injection

To preserve key resolution:

1.  `<keydef>` elements are extracted from the main project map.
2.  They are appended to the standalone DITAMAP:
    -   Under `<backmatter>` for `bookmap`
    -   Directly under root for standard `map`

This maintains consistency with DITA processing expectations.

------------------------------------------------------------------------

## 11. Conref Handling

The script detects elements containing `conref` attributes and:

-   Adds referenced files into processing scope
-   Prevents duplicate processing
-   Ensures content dependencies are included

------------------------------------------------------------------------

## 12. XML Safety and Integrity

The script:

-   Uses `lxml` for strict XML parsing
-   Preserves original DOCTYPE
-   Maintains XML declarations
-   Writes formatted output
-   Logs errors to `error.log`
-   Exits on critical parsing failures

This prevents silent corruption of structured content.

------------------------------------------------------------------------

## 13. Error Handling Strategy

All major operations are wrapped in structured exception handling:

-   XML syntax errors
-   File not found errors
-   Unexpected runtime exceptions

Errors are:

-   Logged to `error.log`
-   Printed to stdout
-   Terminated with non-zero exit status when critical

This makes the script CI/CD safe.

------------------------------------------------------------------------

## 14. Design Principles

This utility was built around the following principles:

-   Deterministic transformation of content
-   No manual intervention required
-   Environment-aware behavior
-   Preservation of DITA structural integrity
-   Controlled rewriting of only unsafe references
-   Idempotent processing

------------------------------------------------------------------------

## 15. Summary

The Standalone Guide Reference Processor enables scalable generation of
independent documentation deliverables from structured DITA ecosystems.

By combining:

-   Reference classification
-   Controlled rewriting
-   Key definition injection
-   Environment-aware URL generation

it ensures standalone outputs remain structurally correct, externally
linked, and production-ready without manual correction.
