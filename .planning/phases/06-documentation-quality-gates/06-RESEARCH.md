# Phase 6: Documentation & Quality Gates - Research

**Researched:** 2026-02-01
**Domain:** Documentation maintenance, pre-commit hooks, CI pipelines
**Confidence:** HIGH

## Summary

This phase updates all project documentation to reflect the post-cleanup codebase (EAPI migration, Python decomposition, MCP SDK 1.25+, UV-based deps), installs pre-commit hooks to prevent future drift, and creates a CI pipeline with security auditing.

The project currently has NO pre-commit hooks installed (no `.husky/` directory, no `.github/` workflows). The `.claude/CI_CD.md` contains a *planned* GitHub Actions workflow but nothing is deployed. Documentation files like `ROADMAP.md` (last updated 2025-10-21) and `README.md` (status as of 2025-10-13) are significantly stale.

**Primary recommendation:** Use Husky + lint-staged for pre-commit hooks, GitHub Actions for CI, and a systematic doc-by-doc staleness audit to determine update scope.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| husky | latest (v9+) | Git hook management | De facto standard for Node.js projects; `npx husky init` creates `.husky/` dir with hook scripts |
| lint-staged | latest (v15+) | Run linters on staged files only | Pairs with husky; runs tasks only on changed files for fast commits |
| pip-audit | latest | Python dependency vulnerability scanning | Official PyPA tool for auditing Python packages against known vulns |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ruff | latest | Python linting + formatting | Fast all-in-one Python linter; replaces black+flake8+isort |
| prettier | latest | Markdown/JSON formatting | Already used implicitly in CI_CD.md plans |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Husky | simple-git-hooks | Lighter but less ecosystem support; Husky is more documented |
| Husky | lefthook | More powerful but heavier; overkill for this project's needs |
| ruff | black + flake8 | Separate tools; ruff is faster and replaces both |

**Installation:**
```bash
# Pre-commit hooks
npm install --save-dev husky lint-staged

# Python linting (add to pyproject.toml dev deps)
uv add --dev ruff pip-audit
```

## Architecture Patterns

### Pre-commit Hook Structure
```
.husky/
├── pre-commit          # Runs lint-staged
```

### lint-staged Configuration (in package.json)
```json
{
  "lint-staged": {
    "*.{ts,js}": ["npx tsc --noEmit", "npm test -- --bail --findRelatedTests"],
    "*.py": ["uv run ruff check --fix", "uv run ruff format"],
    "*.{md,json,yml}": ["prettier --write"]
  }
}
```

### GitHub Actions CI Structure
```
.github/
└── workflows/
    └── ci.yml          # Single workflow with multiple jobs
```

### Pattern 1: Husky + lint-staged Setup
**What:** `npx husky init` creates `.husky/pre-commit` which calls `npx lint-staged`
**When to use:** Every project with Node.js
**Example:**
```bash
# Source: Context7 /typicode/husky
npx husky init
# Then edit .husky/pre-commit to contain: npx lint-staged
```

package.json additions:
```json
{
  "scripts": {
    "prepare": "husky"
  }
}
```

### Pattern 2: GitHub Actions CI with Security Auditing
**What:** CI pipeline that runs tests, type-check, and security audits
**When to use:** Every push/PR
**Example:**
```yaml
name: CI
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm run build
      - run: npm test
      - run: uv run pytest

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm audit --audit-level=moderate
      - run: uv run pip-audit
```

### Pattern 3: "Last Verified" Timestamps
**What:** Add a metadata line to each doc file for staleness tracking
**When to use:** All technical docs in `.claude/` and `docs/`
**Example:**
```markdown
<!-- Last Verified: 2026-02-01 -->
```
Manual approach is appropriate here - automated timestamps would fire on every commit touching any doc, providing no real signal. The value is in a human/AI explicitly verifying content accuracy.

### Anti-Patterns to Avoid
- **Auto-updating timestamps on every commit:** Loses the "verified" semantic; becomes meaningless
- **Running full test suite in pre-commit:** Too slow; use `--findRelatedTests` or limit to changed files
- **Including integration/live tests in CI:** No Z-Library credentials in CI (user confirmed)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git hook installation | Custom `.git/hooks/` scripts | Husky | Cross-platform, survives `git clean`, team-consistent |
| Running linters on staged files | Custom `git diff --cached` parsing | lint-staged | Handles partial staging, file restoration, error codes |
| Python vulnerability scanning | Manual CVE checking | pip-audit | Maintained by PyPA, uses official advisory DB |
| Node vulnerability scanning | Manual review | npm audit | Built into npm, uses GitHub Advisory DB |

**Key insight:** Git hook management has many edge cases (partial staging, binary files, hook paths across platforms). Husky + lint-staged handle all of these.

## Common Pitfalls

### Pitfall 1: ESM + Jest in Pre-commit
**What goes wrong:** Jest with `--experimental-vm-modules` can be slow and flaky in hooks
**Why it happens:** ESM support in Jest is experimental; cold start is slow
**How to avoid:** Use `--bail --findRelatedTests` flags to run minimal tests; consider only running TypeScript compilation check in pre-commit, full tests in CI
**Warning signs:** Pre-commit takes >10 seconds

### Pitfall 2: Husky Not Installing for Contributors
**What goes wrong:** `prepare` script only runs on `npm install`, not `npm ci`
**Why it happens:** `npm ci` skips `prepare` in some versions
**How to avoid:** Use `"prepare": "husky || true"` to gracefully handle CI environments where husky isn't needed
**Warning signs:** CI fails with "husky: command not found"

### Pitfall 3: Documentation Rot Despite Timestamps
**What goes wrong:** "Last Verified" dates are added but never updated
**Why it happens:** No enforcement mechanism
**How to avoid:** During each phase/release, include a doc-review task. The timestamp is a signal for staleness, not a guarantee.
**Warning signs:** Multiple docs with same old date

### Pitfall 4: pip-audit False Positives
**What goes wrong:** pip-audit flags vendored/local packages or transitive deps you can't control
**Why it happens:** Local editable installs and pinned transitive deps
**How to avoid:** Use `--ignore-vuln` for known false positives; document exceptions
**Warning signs:** CI blocking on vulnerabilities in vendored zlibrary fork

### Pitfall 5: npm audit Noise
**What goes wrong:** `npm audit` flags dev-dependency vulnerabilities that don't affect production
**Why it happens:** Dev deps (jest, sinon) have deep dependency trees
**How to avoid:** Use `npm audit --omit=dev` for production-relevant audits, or `--audit-level=high` to filter noise
**Warning signs:** Dozens of moderate-severity findings in test frameworks

## Code Examples

### Husky Pre-commit Hook
```shell
# .husky/pre-commit
npx lint-staged
```

### lint-staged Config for This Project
```json
{
  "lint-staged": {
    "*.{ts,js}": "npm run build",
    "*.py": "uv run ruff check --fix",
    "*.{md,json}": "prettier --write --prose-wrap preserve"
  }
}
```

### GitHub Actions: UV Setup
```yaml
- name: Install UV
  uses: astral-sh/setup-uv@v4

- name: Install Python dependencies
  run: uv sync

- name: Run Python tests
  run: uv run pytest
```

### Setup Script Python Version Check
```bash
# Add to setup-uv.sh
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
REQUIRED="3.10"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "Python $REQUIRED+ required, found $PYTHON_VERSION"
    exit 1
fi
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Husky v4 (`.huskyrc.json`) | Husky v9 (`.husky/` shell scripts) | 2023 | Simpler, faster, shell-native hooks |
| black + flake8 + isort | ruff | 2024 | Single tool, 10-100x faster |
| `pip install` + requirements.txt | UV + pyproject.toml | 2024-2025 | Already adopted in this project |
| Manual CVE checking | pip-audit + npm audit in CI | 2023+ | Automated, advisory-database-backed |

**Deprecated/outdated:**
- Husky v4 config format: Use v9 `.husky/` directory approach
- `.huskyrc.json`: Replaced by shell scripts in `.husky/`

## Staleness Assessment of Current Docs

Based on reading the actual files:

| Document | Last Updated | Staleness | Action |
|----------|-------------|-----------|--------|
| `.claude/ROADMAP.md` | 2025-10-21 | HIGH - references Phase 2 as current, Oct 2025 dates | Full rewrite |
| `README.md` | 2025-10-13 | HIGH - says "As of 2025-10-13", missing EAPI, phases 1-7 | Major update |
| `ISSUES.md` | 2025-11-24 | MEDIUM - has new ISSUE-API-001, but needs triage | Triage + update |
| `.claude/CI_CD.md` | Unknown | HIGH - describes planned workflows that don't exist | Rewrite to match actual CI |
| `.claude/PROJECT_CONTEXT.md` | Unknown | Needs review | Check and update |
| `.claude/ARCHITECTURE.md` | Unknown | Needs review | Check and update |
| `.claude/VERSION_CONTROL.md` | Unknown | Needs review | Check and update |
| `docs/adr/` | Various | MEDIUM - missing ADRs for EAPI, Python decomp, MCP SDK | Backfill 3 ADRs |

## Open Questions

1. **Prettier for this project?**
   - What we know: No prettier config exists currently; CI_CD.md mentions it in planned workflows
   - What's unclear: Whether the project wants to add prettier as a dependency
   - Recommendation: Add prettier for markdown/json formatting in lint-staged; lightweight and valuable

2. **ruff inclusion scope**
   - What we know: No Python linting currently configured
   - What's unclear: Whether to add ruff as a full linter or just formatter
   - Recommendation: Add ruff for both check + format; it's fast and catches real issues

3. **CI test matrix (Node versions)**
   - What we know: CI_CD.md planned Node 18+20 matrix
   - What's unclear: Whether multi-version testing is needed for an MCP server
   - Recommendation: Single Node 18 (LTS) is sufficient; matrix adds CI time for minimal benefit

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/typicode_github_io_husky` - setup, configuration, CI integration
- Context7 `/lint-staged/lint-staged` - configuration patterns, husky integration
- Project files: `package.json`, `pyproject.toml`, `setup-uv.sh`, `.claude/CI_CD.md`, `ISSUES.md`, `README.md`, `.claude/ROADMAP.md`

### Secondary (MEDIUM confidence)
- astral-sh/setup-uv GitHub Action - UV setup in CI (well-documented official action)
- pip-audit (PyPA maintained) - Python security auditing

### Tertiary (LOW confidence)
- None - all findings verified against primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Husky/lint-staged/pip-audit are well-established, verified via Context7
- Architecture: HIGH - Patterns directly from official docs, adapted to this project's structure
- Pitfalls: HIGH - Based on real project constraints (ESM Jest, vendored zlibrary, no credentials in CI)

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable domain, tools change slowly)
