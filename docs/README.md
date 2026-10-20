# docs/ Index

This directory mixes two kinds of documents: **reference** material that is kept
current, and **historical** one-off reports and design explorations preserved for
context. If you are setting up or troubleshooting the server, everything you need
is in the Reference section.

## Reference (kept current)

| Document | What it covers |
|----------|----------------|
| [api.md](api.md) | API reference for all MCP tools |
| [adr/](adr/) | Architecture Decision Records (ADR-001 through ADR-010) |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Setup and runtime troubleshooting |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment paths and edge cases |
| [RETRY_CONFIGURATION.md](RETRY_CONFIGURATION.md) | Retry and circuit-breaker configuration |
| [specifications/](specifications/) | Historical specifications; processing features are parked |
| [text-processing-migration.md](text-processing-migration.md) | Acquisition-only 2.0 migration and preserved text-processing tree |
| [examples/](examples/) | MCP config templates and usage examples |
| [installation/](installation/) | System-wide setup notes |

## Historical (one-off reports and superseded designs)

Preserved for context; not maintained. Details may no longer match the code.

**Architecture and design explorations:**
[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md),
[CITATION_INFERENCE_ARCHITECTURE.md](CITATION_INFERENCE_ARCHITECTURE.md),
[CURRENT_PIPELINE_FLOW.md](CURRENT_PIPELINE_FLOW.md),
[HYBRID_TOC_EXTRACTION.md](HYBRID_TOC_EXTRACTION.md),
[MARGINALIA_DESIGN.md](MARGINALIA_DESIGN.md),
[METADATA_ARCHITECTURE.md](METADATA_ARCHITECTURE.md),
[RAG_PIPELINE_ENHANCEMENTS_V2.md](RAG_PIPELINE_ENHANCEMENTS_V2.md),
[architecture/](architecture/)

**One-off reports and summaries:**
[BOOK_PAGE_METADATA_COMPLETE.md](BOOK_PAGE_METADATA_COMPLETE.md),
[FOOTNOTE_CONTINUATION_QUICKSTART.md](FOOTNOTE_CONTINUATION_QUICKSTART.md),
[IMPLEMENTATION_SUMMARY_HYBRID_TOC.md](IMPLEMENTATION_SUMMARY_HYBRID_TOC.md),
[INT-001-Resolution-Report.md](INT-001-Resolution-Report.md),
[METADATA_VERIFICATION.md](METADATA_VERIFICATION.md),
[TESTING_LESSONS_LEARNED.md](TESTING_LESSONS_LEARNED.md),
[rag-output-qa-report-rerun-20250429.md](rag-output-qa-report-rerun-20250429.md)

**Early specs and plans (pre-dating the current implementation):**
[RESEARCH_TOOLS_SPECIFICATION.md](RESEARCH_TOOLS_SPECIFICATION.md),
[UV_MIGRATION_PLAN.md](UV_MIGRATION_PLAN.md),
[get-book-metadata-spec.md](get-book-metadata-spec.md),
[pdf-processing-implementation-spec.md](pdf-processing-implementation-spec.md),
[project-plan-zlibrary-mcp.md](project-plan-zlibrary-mcp.md),
[rag-markdown-generation-spec.md](rag-markdown-generation-spec.md),
[rag-output-quality-spec.md](rag-output-quality-spec.md),
[rag-pipeline-implementation-spec.md](rag-pipeline-implementation-spec.md),
[rag-robustness-enhancement-spec.md](rag-robustness-enhancement-spec.md),
[mcp-zod-validation-error-research.md](mcp-zod-validation-error-research.md)

**Z-Library site research (pre-EAPI era):**
[Z-LIBRARY_SITE_ANALYSIS.md](Z-LIBRARY_SITE_ANALYSIS.md),
[ZLIBRARY_TECHNICAL_IMPLEMENTATION.md](ZLIBRARY_TECHNICAL_IMPLEMENTATION.md),
[zlibrary_repo_overview.md](zlibrary_repo_overview.md),
[MCP_RECOMMENDATIONS.md](MCP_RECOMMENDATIONS.md),
[MCP_SCRAPING_SETUP.md](MCP_SCRAPING_SETUP.md),
[mcp-reference/](mcp-reference/)

**Deployment-era reports:** [deployment/](deployment/) (validation matrices and
readiness checklists from the v1.2 release cycle)

**Archive:** [archive/](archive/) (explicitly archived analyses and session
reports)

Historical UV migration: [history/MIGRATION_V2.md](history/MIGRATION_V2.md) (old unshipped version label).
