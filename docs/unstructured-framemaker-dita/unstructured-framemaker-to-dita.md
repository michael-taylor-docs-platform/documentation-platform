---
title: Unstructured FrameMaker → DITA XML Pilot
tags:
  - DITA
  - XML
  - Content Engineering
category: Modernization
audience: Hiring Managers
---
## Executive Summary

Led a 4-month executive-sponsored pilot to modernize legacy unstructured FrameMaker documentation into structured DITA XML for Trend Micro’s flagship product, Trend Micro **OfficeScan**. Converted approximately 3,000 XML topic files and 40 DITA maps across 4 user guides while independently researching and implementing advanced reuse strategies using conrefs and conkeyrefs.

Delivered a scalable structured content model and reuse framework that demonstrated viability for broader organizational adoption

## Context

- Organization: Enterprise cybersecurity software company
- Product: Trend Micro OfficeScan (flagship endpoint protection platform)
- Legacy format: Unstructured FrameMaker
- Content volume (pilot scope):
  - 4 content sources (Admistrator's Guide, Installation and Upgrade Guide, Server Online Help, Agent Online Help)
  - ~3,000 XML topic files
  - 40 DITA maps
- Team: 1 (sole contributor during pilot phase)
- Initiative type: Executive-driven modernization effort

At the time, documentation was largely monolithic, difficult to reuse, and constrained by formatting-centric authoring tools.

## The Problem

### Technical Constraints

- Content locked in unstructured FrameMaker format
- Limited reuse capability
- Manual duplication of shared content
- Inconsistent information architecture
- No scalable conditional publishing model

### Operational Constraints

- High visibility (flagship product)
- Executive expectations for modernization
- No existing internal DITA expertise
- Pilot needed to prove ROI before broader adoption

## Strategic Approach

### Technical Strategy

1. Designed a DITA topic-based information architecture
2. Established map hierarchy structure for each content source (40 supporting maps)
3. Researched and implemented:
  - DITA conrefs
  - DITA conkeyrefs
  - Reusable content modules
  - Boilerplate repositories
4. Defined reuse patterns for:
  - Common procedures
  - Shared configuration content
  - Repeated warning and compliance blocks

The most technically demanding aspect was researching and implementing **conref and conkeyref structures** that allowed:

- Centralized reusable content
- Contextual content insertion
- Controlled variable substitution
- Reduced duplication across product variants

This required deep study of DITA linking and key-based reuse models.

### Operational Strategy

- Scoped pilot around flagship product for maximum visibility
- Structured pilot duration to 4 months for measurable evaluation
- Documented architecture decisions for stakeholder transparency
- Maintained parallel legacy stability during transition
- Created internal documentation to support future team adoption

Because the initiative was executive-driven, the pilot had to demonstrate:

- Technical feasibility
- Scalability
- Content maintainability
- Authoring efficiency gains
- Translation cost reduction

## Implementation

- Converted legacy content into modular DITA topics
- Normalized structure
- Established controlled reuse libraries
- Implemented map-level organization strategy
- Validated build consistency across 3,000+ files

All transformation work was performed independently during the pilot phase.

## Outcomes

- Successfully delivered a fully structured DITA content set for OfficeScan
- Demonstrated large-scale topic-based architecture viability
- Reduced content duplication through reuse modeling
- Established structured authoring as a credible modernization path

The pilot validated structured authoring as an enterprise-scale solution rather than an experimental initiative.

## Lessons Learned

1. Reuse modeling must be intentional from the beginning
2. Conkeyref design requires early taxonomy planning
3. Executive sponsorship accelerates modernization initiatives
4. Content migration is both technical and behavioral
5. Structured authoring success depends on governance, not just tooling

