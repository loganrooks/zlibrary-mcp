# claudedocs/ - Project Documentation

**Last Updated**: 2025-10-21
**Organization**: Hierarchical by purpose and topic
**Naming Convention**: kebab-case

---

## 📚 Documentation Structure

```
claudedocs/
├── session-notes/          Development session summaries and handoffs
├── phase-reports/          Phase-specific implementation reports
│   ├── phase-1/           Enhanced data model and foundation
│   └── phase-2/           Quality pipeline and integration
├── architecture/           System design and architectural analysis
├── research/               Topic-specific research and findings
│   ├── strikethrough/     Strikethrough detection research
│   ├── pdf-processing/    PDF quality and formatting research
│   └── metadata/          Metadata extraction research
├── archive/2025-10/       Historical and superseded documents
├── exploration/           Early project exploration
└── strikethrough-research/ Original strikethrough research files
```

---

## 🗂️ Quick Navigation

### For New Contributors
Start here to understand the project:
1. **[Architecture Overview](architecture/rag-pipeline-architecture-analysis.md)** - System design and quality metrics
2. **[Latest Handoff](phase-reports/phase-1/2025-10-15-phase-1-2-handoff.md)** - Current state and next steps
3. **[Recent Session](session-notes/2025-10-18-complete-session-summary.md)** - Latest development session

### For Active Development
Current work context:
- **[Phase 2 Status](phase-reports/phase-2/2025-10-18-phase-2-integration-complete.md)** - Latest phase completion
- **[Implementation Roadmap](architecture/2025-10-18-prioritized-implementation-roadmap.md)** - Prioritized tasks
- **[TDD Infrastructure](session-notes/2025-10-18-tdd-infrastructure-complete.md)** - Testing framework

### For Research
Topic-specific investigations:
- **[Strikethrough Detection](research/strikethrough/)** - *Sous rature* and x-mark detection
- **[PDF Processing](research/pdf-processing/)** - Garbled text and formatting analysis
- **[Metadata Extraction](research/metadata/)** - Enhanced metadata strategies

---

## 📖 Directory Guides

Each subdirectory contains an `INDEX.md` file with:
- Complete file listings with descriptions
- Key concepts and themes
- Navigation links to related documents

**Browse by Directory:**
- [Session Notes →](session-notes/INDEX.md)
- [Architecture →](architecture/INDEX.md)
- [Phase Reports →](phase-reports/INDEX.md)
- [Research →](research/INDEX.md)
- [Archive →](archive/2025-10/INDEX.md)

---

## 🎯 Project Status at a Glance

### Current Branch
`feature/rag-pipeline-enhancements-v2`

### Quality Metrics
- **Current Score**: 41.75/100
- **Target Score**: 75-85/100
- **Content Retention**: 99%+

### Recent Milestones
- ✅ Phase 1: Enhanced data model (100% complete)
- ✅ Phase 2: Quality pipeline integration (in progress)
- ✅ TDD infrastructure established
- 🔄 Phase 2 integration ongoing

---

## 📝 Documentation Standards

### Naming Convention
**kebab-case** for all markdown files:
- ✅ `rag-pipeline-architecture-analysis.md`
- ✅ `2025-10-18-complete-session-summary.md`
- ❌ `RAG_PIPELINE_ANALYSIS.md` (old SCREAMING_CASE)
- ❌ `rag_failure_analysis.md` (old snake_case)

### Date Format
For timestamped documents: `YYYY-MM-DD-descriptive-name.md`
- Example: `2025-10-18-phase-2-integration-complete.md`

### File Organization
- **Session Notes**: Development session summaries with dates
- **Phase Reports**: Phase-specific deliverables and status
- **Architecture**: System design and strategic planning
- **Research**: Topic-specific investigations and findings
- **Archive**: Historical and superseded documents

---

## 🔄 Recent Reorganization

On **2025-10-21**, the claudedocs directory was reorganized from a flat structure with 52 files to a hierarchical structure with proper categorization.

**Key Changes:**
- ✅ All files moved to appropriate subdirectories
- ✅ Standardized kebab-case naming (40 files renamed)
- ✅ Git history preserved (39 tracked files)
- ✅ 10 INDEX.md files created for navigation
- ✅ Comprehensive migration report generated

See **[MIGRATION_REPORT.md](MIGRATION_REPORT.md)** for complete details.

---

## 🛠️ Maintenance

### Adding New Documentation
1. Choose appropriate subdirectory based on purpose
2. Use kebab-case naming convention
3. Add date prefix if timestamped: `YYYY-MM-DD-name.md`
4. Update relevant INDEX.md with description
5. Commit with descriptive message

### Archiving Old Documents
When a document becomes superseded or historical:
1. Move to `archive/YYYY-MM/` (create month directory if needed)
2. Use `git mv` to preserve history
3. Update INDEX.md in both source and destination
4. Add note in archive INDEX.md explaining context

### Cross-References
When linking between documents:
- Use relative paths: `../architecture/file.md`
- Prefer linking to directories via INDEX.md: `[Architecture](../architecture/)`
- Keep links up-to-date when reorganizing

---

## 📊 Documentation Metrics

| Category | Files | Description |
|----------|-------|-------------|
| **Session Notes** | 5 | Development session summaries |
| **Phase Reports** | 8 | Phase-specific implementation reports |
| **Architecture** | 7 | System design and analysis |
| **Research** | 15 | Topic-specific investigations |
| **Archive** | 17 | Historical documents |
| **Navigation** | 10 | INDEX.md files |
| **Total** | 62 | All documentation files |

---

## 🤝 Contributing

When contributing documentation:
1. Follow naming conventions (kebab-case)
2. Place files in appropriate directories
3. Update INDEX.md files
4. Use `git mv` for renames (preserves history)
5. Link related documents
6. Keep migration report style for major reorganizations

---

## 📞 Support

For questions about documentation:
- Check relevant INDEX.md for context
- Review migration report for structural changes
- See [.claude/](../.claude/) for project-wide documentation
- Refer to [CLAUDE.md](../CLAUDE.md) for development guide

---

**Last Reorganization**: 2025-10-21
**Documentation Standard**: kebab-case, hierarchical organization
**Total Files**: 62 (52 original + 10 INDEX files)
