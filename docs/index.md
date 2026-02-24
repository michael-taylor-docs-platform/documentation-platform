# Michael Taylor – Documentation as a Platform

This site demonstrates a deterministic documentation platform architecture built using:

- MkDocs (presentation layer)
- Python ingestion pipeline
- Format-aware transformation (Markdown + DITA)
- GitHub Actions (PR-gated validation)
- Manual promotion workflow
- Enterprise-style governance separation

## Architecture Overview

Source → Transformation → Validation → Publish

Documentation is treated as release-critical infrastructure, not a publishing afterthought.