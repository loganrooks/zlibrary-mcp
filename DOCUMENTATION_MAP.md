# Documentation Map

**Last Updated**: 2025-10-21
**Purpose**: Central navigation for all project documentation

> 📖 **New here?** Start with [README.md](README.md) → [QUICKSTART.md](QUICKSTART.md) → [CLAUDE.md](CLAUDE.md)

---

## Quick Navigation by Role

### 🚀 I want to USE this MCP server
1. [README.md](README.md) - Project overview and features
2. [QUICKSTART.md](QUICKSTART.md) - Fast setup guide
3. [MCP_CONFIG_TEMPLATE.md](MCP_CONFIG_TEMPLATE.md) - Configuration example
4. [SYSTEM_INSTALLATION.md](SYSTEM_INSTALLATION.md) - System dependencies

### 💻 I want to CONTRIBUTE code
1. [.claude/PROJECT_CONTEXT.md](.claude/PROJECT_CONTEXT.md) - Architecture and mission
2. [.claude/PATTERNS.md](.claude/PATTERNS.md) - Code patterns and standards
3. [.claude/TDD_WORKFLOW.md](.claude/TDD_WORKFLOW.md) - Test-driven development process
4. [.claude/VERSION_CONTROL.md](.claude/VERSION_CONTROL.md) - Git workflow and PR process
5. [ISSUES.md](ISSUES.md) - Known issues and priorities

### 🤖 I'm an AI Assistant (Claude Code)
1. [CLAUDE.md](CLAUDE.md) - Complete project context (300 lines)
2. [.claude/](/.claude/) - All development guides (10 essential docs)
3. [ISSUES.md](ISSUES.md) - Current problems and action items
4. [docs/adr/](docs/adr/) - Architecture decisions (ADR-001 through ADR-008)

### 🐛 I need to DEBUG or TROUBLESHOOT
1. [.claude/DEBUGGING.md](.claude/DEBUGGING.md) - Troubleshooting guide
2. [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
3. [TEST_ISSUES.md](TEST_ISSUES.md) - Known test problems
4. [ISSUES.md](ISSUES.md) - All tracked issues

### 🏗️ I want to understand the ARCHITECTURE
1. [.claude/PROJECT_CONTEXT.md](.claude/PROJECT_CONTEXT.md) - Core principles and design
2. [docs/adr/README.md](docs/adr/README.md) - Architecture Decision Records index
3. [docs/architecture/rag-pipeline.md](docs/architecture/rag-pipeline.md) - RAG pipeline architecture
4. [docs/specifications/README.md](docs/specifications/README.md) - Technical specifications catalog

---

## Documentation by Topic

### RAG Pipeline (Document Processing)

**Essential Reading**:
- [.claude/RAG_QUALITY_FRAMEWORK.md](.claude/RAG_QUALITY_FRAMEWORK.md) - Quality verification framework ⭐
- [docs/architecture/rag-pipeline.md](docs/architecture/rag-pipeline.md) - Pipeline architecture
- [docs/RAG_PIPELINE_ENHANCEMENTS_V2.md](docs/RAG_PIPELINE_ENHANCEMENTS_V2.md) - V2 enhancements

**Technical Specifications**:
- [docs/specifications/PHASE_2_INTEGRATION_SPECIFICATION.md](docs/specifications/PHASE_2_INTEGRATION_SPECIFICATION.md) - Phase 2 integration spec
- [docs/specifications/RIGOROUS_REAL_WORLD_TDD_STRATEGY.md](docs/specifications/RIGOROUS_REAL_WORLD_TDD_STRATEGY.md) - TDD strategy for RAG
- [docs/specifications/SELECTIVE_OCR_STRATEGY.md](docs/specifications/SELECTIVE_OCR_STRATEGY.md) - OCR recovery strategy
- [docs/specifications/SOUS_RATURE_RECOVERY_STRATEGY.md](docs/specifications/SOUS_RATURE_RECOVERY_STRATEGY.md) - Strikethrough handling

**Architecture Decisions**:
- [docs/adr/ADR-006-Quality-Pipeline-Architecture.md](docs/adr/ADR-006-Quality-Pipeline-Architecture.md) - Quality pipeline design
- [docs/adr/ADR-007-Phase-2-Integration-Complete.md](docs/adr/ADR-007-Phase-2-Integration-Complete.md) - Phase 2 completion

**Current Status**:
- See [claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md](claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md) - Latest status report
- See [ISSUES.md](ISSUES.md) for known RAG pipeline issues

### MCP Server Development

**Getting Started**:
- [docs/mcp-reference/01-overview.md](docs/mcp-reference/01-overview.md) - MCP protocol overview
- [docs/mcp-reference/guide-for-building-mcp-server.md](docs/mcp-reference/guide-for-building-mcp-server.md) - MCP server development guide
- [.claude/MCP_SERVERS.md](.claude/MCP_SERVERS.md) - Development tools (Playwright, SQLite, etc.)

**Z-Library Integration**:
- [docs/ZLIBRARY_TECHNICAL_IMPLEMENTATION.md](docs/ZLIBRARY_TECHNICAL_IMPLEMENTATION.md) - Implementation details
- [docs/Z-LIBRARY_SITE_ANALYSIS.md](docs/Z-LIBRARY_SITE_ANALYSIS.md) - Site structure analysis
- [docs/zlibrary_repo_overview.md](docs/zlibrary_repo_overview.md) - Repository overview

**Architecture Decisions**:
- [docs/adr/ADR-002-Download-Workflow-Redesign.md](docs/adr/ADR-002-Download-Workflow-Redesign.md) - Download workflow
- [docs/adr/ADR-003-Handle-ID-Lookup-Failure.md](docs/adr/ADR-003-Handle-ID-Lookup-Failure.md) - ID lookup handling
- [docs/adr/ADR-004-Python-Bridge-Path-Resolution.md](docs/adr/ADR-004-Python-Bridge-Path-Resolution.md) - Python path resolution

### Testing and Quality

**Test Strategy**:
- [.claude/TDD_WORKFLOW.md](.claude/TDD_WORKFLOW.md) - Test-driven development workflow ⭐
- [.claude/RAG_QUALITY_FRAMEWORK.md](.claude/RAG_QUALITY_FRAMEWORK.md) - RAG quality verification
- [docs/TESTING_LESSONS_LEARNED.md](docs/TESTING_LESSONS_LEARNED.md) - Testing insights

**Test Issues**:
- [TEST_ISSUES.md](TEST_ISSUES.md) - Known test problems
- [ISSUES.md](ISSUES.md) - All tracked issues

**Performance**:
- [docs/specifications/PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING.md](docs/specifications/PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING.md) - Performance optimization

### Deployment and CI/CD

**Deployment**:
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
- [docs/deployment/DEPLOYMENT_CHECKLIST.md](docs/deployment/DEPLOYMENT_CHECKLIST.md) - Pre-deployment checklist
- [docs/deployment/DEPLOYMENT_READINESS_AND_IMPROVEMENTS.md](docs/deployment/DEPLOYMENT_READINESS_AND_IMPROVEMENTS.md) - Readiness assessment

**CI/CD**:
- [.claude/CI_CD.md](.claude/CI_CD.md) - CI/CD strategy and pipelines
- [docs/deployment/ALL_TOOLS_VALIDATION_MATRIX.md](docs/deployment/ALL_TOOLS_VALIDATION_MATRIX.md) - Tool validation matrix

**Migration Guides**:
- [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md) - V2.0 UV migration
- [docs/UV_MIGRATION_PLAN.md](docs/UV_MIGRATION_PLAN.md) - UV migration planning

### Development Workflow

**Essential Guides**:
- [.claude/VERSION_CONTROL.md](.claude/VERSION_CONTROL.md) - Git workflow, branching, PRs ⭐
- [.claude/PATTERNS.md](.claude/PATTERNS.md) - Code patterns and standards ⭐
- [.claude/DEBUGGING.md](.claude/DEBUGGING.md) - Troubleshooting guide ⭐

**Project Management**:
- [.claude/IMPLEMENTATION_ROADMAP.md](.claude/IMPLEMENTATION_ROADMAP.md) - Current action plan
- [ISSUES.md](ISSUES.md) - Known problems catalog
- [IMPROVEMENT_RECOMMENDATIONS.md](IMPROVEMENT_RECOMMENDATIONS.md) - Enhancement proposals

**Meta-Learning**:
- [.claude/META_LEARNING.md](.claude/META_LEARNING.md) - Lessons learned and insights

---

## Documentation Structure Overview

```
/mcp-servers/zlibrary-mcp/
├── Root Level - Entry points and project overview
│   ├── README.md                    # Project overview
│   ├── CLAUDE.md                    # AI assistant context
│   ├── QUICKSTART.md                # Fast setup
│   ├── ISSUES.md                    # Known issues
│   └── [other project files]
│
├── .claude/ - Living development guides (10 files) ⭐
│   ├── PROJECT_CONTEXT.md           # Mission and architecture
│   ├── IMPLEMENTATION_ROADMAP.md    # Current action plan
│   ├── PATTERNS.md                  # Code patterns
│   ├── RAG_QUALITY_FRAMEWORK.md     # Quality framework
│   ├── TDD_WORKFLOW.md              # Test-driven development
│   ├── DEBUGGING.md                 # Troubleshooting
│   ├── VERSION_CONTROL.md           # Git workflow
│   ├── CI_CD.md                     # CI/CD pipelines
│   ├── MCP_SERVERS.md               # Development tools
│   └── META_LEARNING.md             # Lessons learned
│
├── docs/ - Specifications and architecture
│   ├── adr/ - Architecture Decision Records
│   │   ├── README.md                # ADR index (see below)
│   │   └── ADR-001 through ADR-008
│   │
│   ├── specifications/ - Technical specs (7 large files)
│   │   ├── README.md                # Specification catalog
│   │   ├── PHASE_2_INTEGRATION_SPECIFICATION.md
│   │   ├── RIGOROUS_REAL_WORLD_TDD_STRATEGY.md
│   │   └── [5 other major specs]
│   │
│   ├── architecture/ - Architecture documentation
│   │   ├── rag-pipeline.md
│   │   └── pdf-processing-integration.md
│   │
│   ├── deployment/ - Deployment guides
│   ├── examples/ - Usage examples
│   ├── mcp-reference/ - MCP protocol documentation
│   └── archive/ - Historical documentation
│
├── claudedocs/ - Session reports and analyses
│   ├── strikethrough-research/ - Organized research subdirectory
│   └── [50+ session reports - see recent status reports]
│
└── scripts/ - Utility scripts (see scripts/README.md)
```

---

## Architecture Decision Records (ADRs)

> 📋 See [docs/adr/README.md](docs/adr/README.md) for complete ADR index

**Quick Reference**:
- **ADR-001**: Jest ESM Migration
- **ADR-002**: Download Workflow Redesign ⭐
- **ADR-003**: Handle ID Lookup Failure ⭐
- **ADR-004**: Python Bridge Path Resolution ⭐
- **ADR-005**: [Missing - under investigation]
- **ADR-006**: Quality Pipeline Architecture ⭐
- **ADR-007**: Phase 2 Integration Complete
- **ADR-008**: Stage 2 Independence Correction

---

## Recent Session Reports (Last 30 Days)

> ⚠️ **Status**: Session reports are being reorganized. See [claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md](claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md)

**Most Recent** (2025-10-20 to 2025-10-21):
- [claudedocs/FORMATTING_GROUP_MERGER_ARCHITECTURE.md](claudedocs/FORMATTING_GROUP_MERGER_ARCHITECTURE.md) - Latest formatter work
- [claudedocs/SOUS_RATURE_DETECTION_VALIDATION_2025_10_20.md](claudedocs/SOUS_RATURE_DETECTION_VALIDATION_2025_10_20.md) - Strikethrough validation

**Phase 2 Status** (2025-10-18):
- [claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md](claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md) - Phase 2 completion report
- [claudedocs/RAG_PIPELINE_COMPREHENSIVE_ANALYSIS_2025_10_18.md](claudedocs/RAG_PIPELINE_COMPREHENSIVE_ANALYSIS_2025_10_18.md) - Pipeline analysis

**For Complete Session History**: See `docs/archive/` (being organized)

---

## Document Status Legend

| Status | Meaning | Example |
|--------|---------|---------|
| ⭐ Living | Actively maintained, current source of truth | .claude/ guides |
| 📋 Permanent | Immutable record (ADRs, archived specs) | docs/adr/ |
| 📊 Current | Active specification, implementation in progress | docs/specifications/ |
| 📅 Timestamped | Session report, historical snapshot | claudedocs/ reports |
| 🗄️ Archived | Historical reference, superseded | docs/archive/ |

---

## Frequently Asked Questions

### Where do I find...?

**"The current RAG pipeline architecture?"**
→ [docs/architecture/rag-pipeline.md](docs/architecture/rag-pipeline.md)

**"How to add a new MCP tool?"**
→ [.claude/MCP_SERVERS.md](.claude/MCP_SERVERS.md) + [docs/mcp-reference/guide-for-building-mcp-server.md](docs/mcp-reference/guide-for-building-mcp-server.md)

**"Known issues and priorities?"**
→ [ISSUES.md](ISSUES.md)

**"Git workflow and PR process?"**
→ [.claude/VERSION_CONTROL.md](.claude/VERSION_CONTROL.md)

**"Why was this design decision made?"**
→ [docs/adr/README.md](docs/adr/README.md) (search by topic)

**"How to run tests?"**
→ [.claude/TDD_WORKFLOW.md](.claude/TDD_WORKFLOW.md)

**"Deployment checklist?"**
→ [docs/deployment/DEPLOYMENT_CHECKLIST.md](docs/deployment/DEPLOYMENT_CHECKLIST.md)

**"What changed in the last session?"**
→ Check most recent file in [claudedocs/](claudedocs/) with today's date

---

## Contributing to Documentation

**Before Creating a New Document**:
1. Check this map - does similar documentation already exist?
2. Review [.claude/PATTERNS.md](.claude/PATTERNS.md) for documentation standards
3. Consider updating existing "living" documents instead

**Document Naming Conventions**:
- Living guides: `TOPIC_NAME.md` (UPPERCASE_UNDERSCORES)
- ADRs: `ADR-NNN-Title-In-Kebab-Case.md`
- Session reports: `YYYY-MM-DD-topic-description.md`
- Specifications: `descriptive-name-in-kebab-case.md`

**Where to Put New Documents**:
- Development guides → `.claude/`
- Architecture decisions → `docs/adr/`
- Technical specifications → `docs/specifications/`
- Session reports → `claudedocs/`
- User-facing guides → `docs/`

**After Creating Documentation**:
- Add cross-references to related documents
- Update this map if creating major new section
- Link from CLAUDE.md if relevant to AI assistants

---

## Documentation Health

**Last Full Audit**: 2025-10-21
**Known Issues**:
- ADR-005 missing from sequence (under investigation)
- ~50 session reports need archival organization
- memory-bank/ directory status unclear (41 files)

**Planned Improvements**:
- Automated link checker (CI)
- Session report archival process
- Cross-reference enhancement

See [claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md](claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md) for complete reorganization plan.

---

## Quick Command Reference

```bash
# Find documentation by keyword
grep -r "keyword" docs/ .claude/ claudedocs/ --include="*.md"

# List all ADRs
ls docs/adr/ADR-*.md

# Find recent session reports
ls -lt claudedocs/*.md | head -10

# Check for broken links (coming soon)
# npm run docs:check-links
```

---

**Metadata**:
- Created: 2025-10-21
- Last Updated: 2025-10-21
- Maintained by: Project contributors
- Related: [claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md](claudedocs/DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md)
