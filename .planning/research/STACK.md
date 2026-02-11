# Stack Research: v1.2 Production Readiness

**Domain:** MCP server production readiness (npm publishing, API docs, test infrastructure, repo cleanup)
**Researched:** 2026-02-11
**Confidence:** HIGH (most recommendations verified against official docs and npm registry)

## Context: What Already Exists (DO NOT Change)

The following stack is validated and locked. v1.2 adds tooling around it, not replacements.

| Existing | Version | Status |
|----------|---------|--------|
| Node.js | 22 LTS | Locked |
| TypeScript | ^5.5.3 | Locked |
| @modelcontextprotocol/sdk | ^1.25.3 | Locked |
| Zod | ^3.25.76 | Locked (MCP SDK dependency) |
| Jest | ^29.7.0 | Locked |
| ts-jest | ^29.3.2 | Locked |
| Husky | ^9.1.7 | Locked |
| lint-staged | ^16.2.7 | Locked |
| Python | >=3.10 | Locked |
| UV | latest | Locked |
| Pytest | >=8.4.0 | Locked |
| Ruff | >=0.14.14 | Locked |

## Recommended Stack Additions

### 1. npm Publishing Readiness

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| (no new deps) | - | Shebang already present in src/index.ts | Already has `#!/usr/bin/env node` |
| npm (builtin) | >=9.5.0 | `npm pack --dry-run` for pre-publish validation | Zero-dep way to verify package contents |
| npm provenance | npm >=9.5.0 | Supply chain security attestation | Standard for 2026 npm packages; builds trust |

**What needs to change (config only, no new packages):**

1. **package.json `files` field** (CRITICAL): Currently absent. The `.npmignore` is incomplete (missing `__tests__/`, `test_files/`, `docs/`, `.claude/`, `.planning/`, `claudedocs/`, `lib/` Python scripts that should be included, etc.). Use whitelist approach:
   ```json
   "files": [
     "dist/",
     "lib/",
     "zlibrary/",
     "setup-uv.sh",
     "pyproject.toml",
     "uv.lock",
     "README.md",
     "LICENSE"
   ]
   ```
   Rationale: `files` is a whitelist -- safer than `.npmignore` blacklist. Prevents accidental leakage of test PDFs (large), ground truth data, internal docs, and planning files.

2. **package.json corrections**:
   - `"main"` should be `"dist/index.js"` (currently `"index.js"` which does not exist)
   - `"private"` field is absent -- verify it should NOT be set to `true`
   - `"engines"` already correct (`"node": ">=22"`)
   - `"bin"` already correct (`"zlibrary-mcp": "./dist/index.js"`)

3. **GitHub Actions publish workflow**: Add a release job to `.github/workflows/ci.yml` triggered on version tags. Requires `permissions: { id-token: write, contents: read }` for npm provenance/trusted publishing.

4. **npm prepublishOnly**: Already exists (`"prepublishOnly": "npm run build"`) -- good.

### 2. API Documentation Generation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| typedoc | ^0.28.16 | TypeScript API docs generation | De facto standard for TS projects; supports TS 5.9, ESM/NodeNext |
| typedoc-plugin-markdown | ^4.4.0 | Markdown output from TypeDoc | GitHub-native docs; no hosting needed; reviewable in PRs |

**Why TypeDoc over alternatives:**
- TypeDoc reads `tsconfig.json` natively -- zero duplication of config
- v0.28 is ESM-native (matches project's `"type": "module"`)
- Generates both HTML (for GitHub Pages) and Markdown (for repo docs)
- 100+ plugins available for customization
- Alternative `api-extractor` is overkill for a single-package MCP server

**Configuration** (create `typedoc.json` at project root):
```json
{
  "entryPoints": ["src/index.ts"],
  "out": "docs/api",
  "plugin": ["typedoc-plugin-markdown"],
  "readme": "none",
  "excludePrivate": true,
  "excludeInternal": true
}
```

**Script addition**:
```json
"scripts": {
  "docs": "typedoc",
  "docs:html": "typedoc --out docs/api-html"
}
```

### 3. Test Infrastructure -- Ground Truth Schema Validation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| ajv | ^8.17.1 | JSON Schema validation for ground truth files | Fastest JSON Schema validator; supports draft-07 (matching existing schemas) |
| ajv-formats | ^3.0.1 | Format validation (date, uri, etc.) for Ajv | Ground truth schema uses `"format": "date"` |

**Why Ajv and not Zod for ground truth validation:**
- Ground truth schemas are already written in JSON Schema draft-07 (3 schema versions: v1, v2, v3)
- Rewriting 524 lines of JSON Schema as Zod would be wasteful and error-prone
- Ajv validates JSON Schema natively; Zod would require `json-schema-to-zod` conversion
- Zod 3.x (locked by MCP SDK) does NOT have `z.toJSONSchema()` -- that is a Zod v4 feature
- Ajv is a devDependency only -- zero impact on production bundle

**ESM compatibility note:** Ajv 8.x works with ESM via `import Ajv from "ajv"`. There are known edge cases with TypeScript `"module": "NodeNext"` that require `import Ajv from "ajv"` (default import) rather than named imports. This is well-documented and straightforward.

**Usage pattern for test infrastructure:**
```typescript
import Ajv from "ajv";
import addFormats from "ajv-formats";
import schema from "../test_files/ground_truth/schema_v3.json" assert { type: "json" };

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
const validate = ajv.compile(schema);

// In test:
const groundTruth = JSON.parse(fs.readFileSync(groundTruthPath, "utf-8"));
const valid = validate(groundTruth);
if (!valid) console.error(validate.errors);
expect(valid).toBe(true);
```

### 4. Automated RAG Quality Scoring (Python side)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest-json-report | >=1.5.0 | JSON output from pytest for CI parsing | Structured test results for quality dashboard / CI gates |
| (no scikit-learn) | - | NOT recommended | Overkill -- precision/recall can be computed with 10 lines of Python |

**Why NOT scikit-learn for quality scoring:**
- Precision/recall/F1 for footnote detection is trivially computed: `tp / (tp + fp)`, `tp / (tp + fn)`
- Adding scikit-learn adds 50+ MB of transitive dependencies (numpy, scipy, etc.)
- The project already has a quality scoring pipeline in `lib/rag/` modules
- Write a small `lib/rag/quality_scorer.py` utility instead

**Quality scoring implementation pattern** (no new deps):
```python
def compute_precision_recall(detected: list, ground_truth: list, match_fn) -> dict:
    tp = sum(1 for d in detected if any(match_fn(d, gt) for gt in ground_truth))
    fp = len(detected) - tp
    fn = sum(1 for gt in ground_truth if not any(match_fn(d, gt) for d in detected))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}
```

**CI integration pattern:**
```yaml
# In .github/workflows/ci.yml
- run: uv run pytest --json-report --json-report-file=test-results.json
- run: python scripts/check_quality_gate.py test-results.json
```

### 5. Structured RAG Output Format

**No new dependencies needed.** The output format is a design/code change, not a library addition.

Current output structure:
```
processed_rag_output/
  {Author}_{Title}_{ID}.pdf.processed.markdown
  {Author}_{Title}_{ID}.pdf.metadata.json
```

Recommended v1.2 structure (separate linked files):
```
processed_rag_output/
  {Author}_{Title}_{ID}/
    body.md              # Main body text
    footnotes.md         # All footnotes, linked by marker
    metadata.json        # Enhanced metadata (source, TOC, page mapping)
    quality.json         # Quality scores (NEW)
```

This is pure Python code changes in `lib/rag/` -- no library additions needed.

### 6. Repo Cleanup Tooling

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| knip | ^5.83.1 | Dead code / unused dependency / unused file detection | 100+ plugins including Jest; finds unused exports, files, dependencies |

**Why Knip:**
- Single tool replaces depcheck + ts-prune + manual file hunting
- Has Jest plugin (understands test file patterns)
- Has TypeScript plugin (understands TS config)
- Has GitHub Actions plugin (understands CI workflows)
- `--fix` flag can auto-remove unused exports
- Runs as `npx knip` -- can be devDependency or even run without install

**Configuration** (create `knip.json` at project root):
```json
{
  "entry": ["src/index.ts"],
  "project": ["src/**/*.ts"],
  "ignore": ["dist/**", "zlibrary/**"],
  "ignoreDependencies": ["python-shell"]
}
```

Note: `python-shell` will likely be flagged because it is used dynamically. The `ignoreDependencies` field handles this.

**What Knip will find in this project:**
- Unused devDependencies (e.g., `@types/supertest`, `supertest` if no HTTP tests remain)
- Dead exports in `src/lib/` modules
- Orphaned files in `src/` or `lib/` not imported anywhere
- Unused test utilities

## Installation

```bash
# Dev dependencies (Node.js)
npm install -D typedoc@^0.28.16 typedoc-plugin-markdown@^4.4.0 ajv@^8.17.1 ajv-formats@^3.0.1 knip@^5.83.1

# Python dev dependencies (add to pyproject.toml [tool.uv] dev-dependencies)
# pytest-json-report>=1.5.0
```

**Total new devDependencies: 5 (Node) + 1 (Python)**
**Total new production dependencies: 0**

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| TypeDoc | api-extractor (@microsoft) | Multi-package monorepos needing .d.ts rollup and API review |
| TypeDoc | documentation.js | Pure JavaScript projects (no TypeScript support needed) |
| typedoc-plugin-markdown | Default TypeDoc HTML | If hosting docs on GitHub Pages with full-featured UI |
| Ajv | Zod schema validation | If ground truth schemas were written in Zod (they are not) |
| Ajv | joi | Legacy projects; Ajv is faster and supports more JSON Schema drafts |
| knip | depcheck + ts-prune | If you only need dependency checking without dead code detection |
| knip | eslint no-unused-vars | Only catches unused variables, not unused files or dependencies |
| pytest-json-report | Custom pytest plugin | If JSON report format does not match your needs |
| Custom precision/recall | scikit-learn metrics | If you need advanced ML metrics (ROC curves, AUC, etc.) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Zod v4 | MCP SDK 1.25.3 depends on Zod 3.25.x; upgrading causes `w._parse is not a function` errors | Stay on Zod ^3.25.76 |
| zod-to-json-schema | Deprecated as of Nov 2025; Zod v4 has native `z.toJSONSchema()` but we cannot use Zod v4 | Use Ajv to validate existing JSON Schemas directly |
| scikit-learn | 50+ MB of dependencies for 10 lines of precision/recall math | Write a 20-line utility function |
| depcheck | Superseded by knip which does everything depcheck does plus more | Use knip |
| ts-prune | Unmaintained; knip is recommended replacement (by ts-prune author) | Use knip |
| api-extractor | Designed for multi-package monorepos; heavy config burden for single-package | Use TypeDoc |
| semantic-release | Over-engineered for a project that does manual releases | Use `npm version` + git tags + manual/CI publish |
| JSDoc | TypeDoc understands TypeScript natively; JSDoc requires redundant annotations | Use TypeDoc |
| npm trusted publishing (Node 24) | Requires Node 24+ for npm >=11.5.1; project is on Node 22 | Use classic npm provenance with `--provenance` flag on npm >=9.5.0 |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| typedoc@0.28.x | TypeScript 5.x | Supports TS 5.5-5.9; ESM native since 0.28.0 |
| typedoc@0.28.x | `"module": "NodeNext"` | Reads tsconfig.json directly; works with project's current config |
| typedoc-plugin-markdown@4.x | typedoc@0.28.x | Must use 4.x series with typedoc 0.28.x |
| ajv@8.x | JSON Schema draft-07 | Project's ground truth schemas use draft-07; this is Ajv's default |
| ajv@8.x | Node 22 ESM | Works with `import Ajv from "ajv"` in ESM mode |
| knip@5.x | Node 22 | Requires Node 18.6+; compatible with project's Node 22 |
| knip@5.x | Jest 29 | Built-in Jest plugin recognizes test patterns |
| pytest-json-report | Pytest 8.x | Compatible with project's pytest >=8.4.0 |
| Zod 3.25.x | MCP SDK 1.25.3 | MUST remain on 3.x; SDK has Zod 3.x as peer dependency |

## Stack Patterns by Feature

**For test infrastructure reorganization:**
- Use Ajv to validate all ground truth JSON files against schema_v3.json
- Add a `validate-ground-truth` npm script that runs Ajv validation
- Create a unified test runner script that validates ground truth THEN runs tests

**For structured RAG output:**
- No new deps; refactor `lib/rag/` Python modules to output to subdirectories
- Add `quality.json` output alongside existing `body.md` and `metadata.json`
- Use existing JSON Schema approach (validated by Ajv) for output format specification

**For automated quality scoring:**
- Write `lib/rag/quality_scorer.py` (pure Python, no deps)
- Use pytest-json-report for CI-parseable test results
- Add CI step that reads JSON report and fails if quality scores drop below thresholds

**For API docs generation:**
- TypeDoc reads existing tsconfig.json and src/index.ts entry point
- typedoc-plugin-markdown generates docs/api/ for GitHub consumption
- Add `docs` script to package.json; optionally run in CI

**For repo cleanup:**
- Run `npx knip` to identify dead files, unused deps, and unused exports
- Review output manually (knip may false-positive on dynamic imports like python-shell)
- Remove confirmed dead files, update package.json deps

**For npm publishing:**
- Add `files` field to package.json (whitelist approach)
- Fix `main` field to point to `dist/index.js`
- Add `npm pack --dry-run` as a CI validation step
- Add publish workflow triggered on git tags

## Sources

- [TypeDoc official site](https://typedoc.org/) -- version 0.28.16, ESM support, configuration (HIGH confidence)
- [TypeDoc npm](https://www.npmjs.com/package/typedoc) -- version verification (HIGH confidence)
- [typedoc-plugin-markdown](https://github.com/typedoc2md/typedoc-plugin-markdown) -- Markdown output plugin (HIGH confidence)
- [Ajv official docs](https://ajv.js.org/) -- version 8.17.1, JSON Schema draft-07 support (HIGH confidence)
- [Ajv npm](https://www.npmjs.com/package/ajv) -- version verification (HIGH confidence)
- [Knip official site](https://knip.dev/) -- dead code detection, plugin ecosystem (HIGH confidence)
- [knip npm](https://www.npmjs.com/package/knip) -- version 5.83.1 (HIGH confidence)
- [pytest-json-report PyPI](https://pypi.org/project/pytest-json-report/) -- JSON test reports (HIGH confidence)
- [npm docs: files field](https://github.com/npm/cli/wiki/Files-&-Ignores) -- package content control (HIGH confidence)
- [MCP server npm publishing guide](https://www.aihero.dev/publish-your-mcp-server-to-npm) -- shebang, bin, npx patterns (MEDIUM confidence)
- [npm provenance with GitHub Actions](https://www.thecandidstartup.org/2026/01/26/bootstrapping-npm-provenance-github-actions.html) -- provenance attestation workflow (MEDIUM confidence)
- [MCP SDK + Zod compatibility](https://github.com/modelcontextprotocol/typescript-sdk/issues/906) -- Zod v3/v4 issues (HIGH confidence)
- [Zod v4 JSON Schema](https://zod.dev/json-schema) -- native toJSONSchema in v4 only (HIGH confidence)
- [zod-to-json-schema deprecation](https://www.npmjs.com/package/zod-to-json-schema) -- deprecated Nov 2025 (HIGH confidence)
- [scikit-learn precision_recall](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html) -- overkill assessment basis (HIGH confidence)

---
*Stack research for: Z-Library MCP Server v1.2 Production Readiness*
*Researched: 2026-02-11*
