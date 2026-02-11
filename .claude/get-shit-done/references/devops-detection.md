# DevOps Detection Reference

Specification for detecting existing DevOps configuration, asking adaptive questions about gaps, and storing context for downstream agents.

**Principle:** Detect first, ask about gaps only. Maximum 3-5 questions. Skip entirely for greenfield projects with no signals.

## Overview

**Purpose:** During `/gsd:new-project` initialization (Phase 5.7), detect existing DevOps configuration in the project, ask adaptive questions about gaps, and store the resolved context in `.planning/config.json` for downstream agent consumption.

**Scope:**
- CI/CD pipeline configuration
- Deployment targets and infrastructure
- Commit conventions
- Git hygiene (`.gitignore`, `.gitattributes`, env templates)
- Environment differentiation (dev/staging/production)

**Storage target:** `.planning/config.json` `devops` section (machine-readable for agent consumption).

**Core behavior:**
1. Run file-based detection patterns to discover existing configuration
2. For each detected item: record in config, do NOT ask the user (already known)
3. For each gap: add to question candidates
4. Select top 3-5 questions from candidates based on project type
5. Store combined results (detections + user answers) in config.json

## Detection Patterns

File-based patterns for detecting existing DevOps configuration. Run these checks against the project root directory.

### CI/CD Detection

| Pattern | Provider | Check |
|---------|----------|-------|
| `.github/workflows/` directory | GitHub Actions | `[ -d ".github/workflows" ]` |
| `.gitlab-ci.yml` | GitLab CI | `[ -f ".gitlab-ci.yml" ]` |
| `.circleci/config.yml` | CircleCI | `[ -f ".circleci/config.yml" ]` |
| `Jenkinsfile` | Jenkins | `[ -f "Jenkinsfile" ]` |
| `bitbucket-pipelines.yml` | Bitbucket Pipelines | `[ -f "bitbucket-pipelines.yml" ]` |
| `.travis.yml` | Travis CI | `[ -f ".travis.yml" ]` |

**Shell pattern:**
```bash
DEVOPS_CI="none"
[ -d ".github/workflows" ] && DEVOPS_CI="github-actions"
[ -f ".gitlab-ci.yml" ] && DEVOPS_CI="gitlab-ci"
[ -f ".circleci/config.yml" ] && DEVOPS_CI="circleci"
[ -f "Jenkinsfile" ] && DEVOPS_CI="jenkins"
[ -f "bitbucket-pipelines.yml" ] && DEVOPS_CI="bitbucket-pipelines"
[ -f ".travis.yml" ] && DEVOPS_CI="travis-ci"
```

**Note:** If multiple CI providers detected, record the first match. This is uncommon but possible during migration.

### Deployment Target Detection

| Pattern | Target | Check |
|---------|--------|-------|
| `vercel.json` or `.vercel/` | Vercel | `[ -f "vercel.json" ] \|\| [ -d ".vercel" ]` |
| `Dockerfile` or `docker-compose.yml` | Docker/Container | `[ -f "Dockerfile" ] \|\| [ -f "docker-compose.yml" ]` |
| `fly.toml` | Fly.io | `[ -f "fly.toml" ]` |
| `railway.json` or `railway.toml` | Railway | `[ -f "railway.json" ] \|\| [ -f "railway.toml" ]` |
| `netlify.toml` | Netlify | `[ -f "netlify.toml" ]` |
| `serverless.yml` or `serverless.yaml` | Serverless Framework | `[ -f "serverless.yml" ] \|\| [ -f "serverless.yaml" ]` |
| `cdk.json` or `template.yaml` (SAM) | AWS | `[ -f "cdk.json" ] \|\| [ -f "template.yaml" ]` |
| `app.yaml` (GCP) | Google Cloud | `[ -f "app.yaml" ]` |

**Shell pattern:**
```bash
DEVOPS_DEPLOY="none"
[ -f "vercel.json" ] || [ -d ".vercel" ] && DEVOPS_DEPLOY="vercel"
[ -f "Dockerfile" ] || [ -f "docker-compose.yml" ] && DEVOPS_DEPLOY="docker"
[ -f "fly.toml" ] && DEVOPS_DEPLOY="fly-io"
[ -f "railway.json" ] || [ -f "railway.toml" ] && DEVOPS_DEPLOY="railway"
[ -f "netlify.toml" ] && DEVOPS_DEPLOY="netlify"
[ -f "serverless.yml" ] || [ -f "serverless.yaml" ] && DEVOPS_DEPLOY="serverless"
[ -f "cdk.json" ] || [ -f "template.yaml" ] && DEVOPS_DEPLOY="aws"
[ -f "app.yaml" ] && DEVOPS_DEPLOY="gcp"
```

### Commit Convention Detection

Check the last 20 git commits for conventional commit patterns.

**Shell pattern:**
```bash
CONVENTIONAL=$(git log --oneline -20 2>/dev/null | grep -cE "^[a-f0-9]+ (feat|fix|chore|docs|style|refactor|test|ci|build|perf)\(" || echo "0")
TOTAL=$(git log --oneline -20 2>/dev/null | wc -l | tr -d ' ')
DEVOPS_COMMITS="freeform"
if [ "$TOTAL" -gt "0" ] && [ "$CONVENTIONAL" -gt "$((TOTAL / 2))" ]; then
  DEVOPS_COMMITS="conventional"
fi
```

**Rules:**
- If >50% of last 20 commits match conventional pattern: `"conventional"`
- Otherwise: `"freeform"`
- If no commits exist (fresh repo): `"none"` (treat as gap)

### Git Hygiene Detection

**Shell pattern:**
```bash
HAS_GITIGNORE=$([ -f ".gitignore" ] && echo "true" || echo "false")
HAS_GITATTRIBUTES=$([ -f ".gitattributes" ] && echo "true" || echo "false")
BRANCH_COUNT=$(git branch 2>/dev/null | wc -l | tr -d ' ' || echo "0")
```

**Checks:**
| Signal | Detection | Gap if |
|--------|-----------|--------|
| `.gitignore` exists | `[ -f ".gitignore" ]` | Missing entirely |
| `.gitattributes` exists | `[ -f ".gitattributes" ]` | Missing (informational, low priority) |
| Branch count | `git branch \| wc -l` | Only relevant for context, not a gap |

### Environment Detection

**Shell pattern:**
```bash
HAS_ENV_TEMPLATE=$([ -f ".env.example" ] || [ -f ".env.template" ] && echo "true" || echo "false")
HAS_ENV_DIFF=$(ls .env.* 2>/dev/null | grep -v ".example\|.template" | wc -l | tr -d ' ')
HAS_DOCKER_PROFILES=$(ls docker-compose.*.yml 2>/dev/null | wc -l | tr -d ' ')
```

**Checks:**
| Signal | Detection | Indicates |
|--------|-----------|-----------|
| `.env.example` or `.env.template` | File existence | Has environment template |
| Multiple `.env.*` files | File count | Has environment differentiation |
| `docker-compose.*.yml` variants | File count | Has Docker environment profiles |

### Combined Detection Script

Run all detections together for efficiency:

```bash
# CI/CD detection
DEVOPS_CI="none"
[ -d ".github/workflows" ] && DEVOPS_CI="github-actions"
[ -f ".gitlab-ci.yml" ] && DEVOPS_CI="gitlab-ci"
[ -f ".circleci/config.yml" ] && DEVOPS_CI="circleci"
[ -f "Jenkinsfile" ] && DEVOPS_CI="jenkins"
[ -f "bitbucket-pipelines.yml" ] && DEVOPS_CI="bitbucket-pipelines"
[ -f ".travis.yml" ] && DEVOPS_CI="travis-ci"

# Deployment detection
DEVOPS_DEPLOY="none"
[ -f "vercel.json" ] || [ -d ".vercel" ] && DEVOPS_DEPLOY="vercel"
[ -f "Dockerfile" ] || [ -f "docker-compose.yml" ] && DEVOPS_DEPLOY="docker"
[ -f "fly.toml" ] && DEVOPS_DEPLOY="fly-io"
[ -f "railway.json" ] || [ -f "railway.toml" ] && DEVOPS_DEPLOY="railway"
[ -f "netlify.toml" ] && DEVOPS_DEPLOY="netlify"
[ -f "serverless.yml" ] || [ -f "serverless.yaml" ] && DEVOPS_DEPLOY="serverless"
[ -f "cdk.json" ] || [ -f "template.yaml" ] && DEVOPS_DEPLOY="aws"
[ -f "app.yaml" ] && DEVOPS_DEPLOY="gcp"

# Commit convention detection
CONVENTIONAL=$(git log --oneline -20 2>/dev/null | grep -cE "^[a-f0-9]+ (feat|fix|chore|docs|style|refactor|test|ci|build|perf)\(" || echo "0")
TOTAL=$(git log --oneline -20 2>/dev/null | wc -l | tr -d ' ')
DEVOPS_COMMITS="freeform"
if [ "$TOTAL" -gt "0" ] && [ "$CONVENTIONAL" -gt "$((TOTAL / 2))" ]; then
  DEVOPS_COMMITS="conventional"
fi

# Git hygiene
HAS_GITIGNORE=$([ -f ".gitignore" ] && echo "true" || echo "false")
HAS_ENV_TEMPLATE=$([ -f ".env.example" ] || [ -f ".env.template" ] && echo "true" || echo "false")

echo "CI: $DEVOPS_CI"
echo "Deploy: $DEVOPS_DEPLOY"
echo "Commits: $DEVOPS_COMMITS"
echo "Gitignore: $HAS_GITIGNORE"
echo "Env template: $HAS_ENV_TEMPLATE"
```

## Adaptive Question Rules

### Skip Condition

**Skip the DevOps round entirely when ALL of these are true:**
- Greenfield project (no existing code detected in Phase 1 setup)
- No CI files detected
- No deploy config detected
- User did not mention deployment, CI, production, or release during Phase 3 questioning

**Rationale:** Greenfield projects with no DevOps signals have nothing to detect and nothing to ask about. Users will add DevOps when ready. Asking premature questions adds friction without value.

### Question Selection Logic

1. Run all detection patterns (Section 2)
2. For each DETECTED item: record in config.json, do NOT ask about it
3. For each GAP (detection returned "none" or missing file): add to question candidate list
4. Filter candidates based on project type (see below)
5. Select top 3-5 questions from filtered candidates

### Project Type Heuristics

**Production app** (has deploy config OR user mentioned "production/deploy/release/hosting" during questioning):
- Ask about: CI pipeline, environments, deployment strategy, commit conventions
- Priority: CI > deploy > environments > commits

**Library/package** (has `package.json` with no deploy config, or user mentioned "library/package/npm/publish"):
- Ask about: CI pipeline, publish target, versioning, commit conventions
- Priority: CI > publish > commits

**Personal tool/experiment** (no signals, user described as "personal/experiment/learning/side project"):
- Ask 1-2 max: Only CI and commit convention
- Skip: deployment, environments, advanced git hygiene

### Question Templates

Ask only about gaps. Use AskUserQuestion for each.

| Gap Detected | Question | Options |
|--------------|----------|---------|
| No CI detected | "No CI/CD pipeline detected. Do you use one?" | GitHub Actions / GitLab CI / CircleCI / Other / None for now |
| No deploy target | "Where does this project deploy?" | Vercel / Docker / AWS / Fly.io / Netlify / Other / Not decided yet |
| Freeform commits | "Your repo uses freeform commit messages. Want to adopt conventional commits?" | Yes, adopt conventional commits / Keep freeform |
| No `.gitignore` | "No `.gitignore` file detected. Add standard ignores for this project type?" | Yes / No |
| No env template | "Environment variables appear to be used but no `.env.example` template exists. Create one?" | Yes / No / No env vars used |
| No environments defined | "Do you have separate environments (staging, production)?" | Yes (describe) / Production only / Not yet |
| No commits (fresh repo) | "What commit convention do you prefer?" | Conventional commits / Freeform |

### Question Limit

- **Hard maximum:** 5 questions per DevOps round
- **Soft target:** 3 questions (typical for most projects)
- **Minimum for production app with many gaps:** 3
- **Maximum for personal tool:** 2

If more than 5 gaps detected, prioritize by project type (see priority lists above) and skip the rest. Record skipped gaps as "not configured" in config.json -- they can be addressed later via `/gsd:settings` or health check recommendations.

## Gap Analysis for Codebase Mapper

DevOps gaps that the codebase mapper's concerns explorer should detect and include in the CONCERNS.md "DevOps Gaps" section.

### Gap Detection Rules

| Condition | Gap Description | Risk |
|-----------|----------------|------|
| Tests exist (`tests/` or `__tests__/` or `*.test.*`) but no CI config | "Tests exist but no CI pipeline to run them" | Tests rot silently, regressions go undetected |
| No `.gitignore` file | "No `.gitignore` file (risk of committing secrets/artifacts)" | Secrets, build artifacts, or `node_modules` committed |
| Env vars referenced in code but no `.env.example` | "Environment variables used but no `.env.example` template" | New developers cannot set up project |
| No README or README has no deploy instructions | "No deployment documentation" | Deployment knowledge is tribal, not documented |
| `Dockerfile` exists but no `.dockerignore` | "Dockerfile exists but no `.dockerignore`" | Docker images bloated with unnecessary files |
| CI config exists but no test step | "CI pipeline exists but does not run tests" | False confidence in CI (pipeline passes without testing) |
| Deploy config exists but no staging environment | "Production deployment configured without staging" | Changes go directly to production without testing |

### Gap Detection Shell Patterns

```bash
# Tests exist but no CI
HAS_TESTS=$(find . -name "*.test.*" -o -name "*.spec.*" -o -name "__tests__" -o -name "tests" 2>/dev/null | grep -v node_modules | head -1)
HAS_CI=$([ -d ".github/workflows" ] || [ -f ".gitlab-ci.yml" ] || [ -f ".circleci/config.yml" ] || [ -f "Jenkinsfile" ] && echo "true" || echo "false")
if [ -n "$HAS_TESTS" ] && [ "$HAS_CI" = "false" ]; then
  echo "GAP: Tests exist but no CI pipeline to run them"
fi

# No .gitignore
if [ ! -f ".gitignore" ]; then
  echo "GAP: No .gitignore file"
fi

# Dockerfile without .dockerignore
if [ -f "Dockerfile" ] && [ ! -f ".dockerignore" ]; then
  echo "GAP: Dockerfile exists but no .dockerignore"
fi

# Environment variables used but no template
if [ ! -f ".env.example" ] && [ ! -f ".env.template" ]; then
  ENV_REFS=$(grep -rl "process\.env\|os\.environ\|env::" --include="*.ts" --include="*.js" --include="*.py" --include="*.go" . 2>/dev/null | grep -v node_modules | head -1)
  if [ -n "$ENV_REFS" ]; then
    echo "GAP: Environment variables used but no .env.example template"
  fi
fi
```

These gaps appear in CONCERNS.md under the "DevOps Gaps" section and feed into health check findings.

## Config Storage

Store DevOps context in `.planning/config.json` under the `devops` section.

### Schema

```json
{
  "devops": {
    "ci_provider": "github-actions|gitlab-ci|circleci|jenkins|bitbucket-pipelines|travis-ci|none",
    "deploy_target": "vercel|docker|fly-io|railway|netlify|serverless|aws|gcp|none",
    "commit_convention": "conventional|freeform",
    "environments": ["development", "staging", "production"],
    "detected": {
      "ci_files": [".github/workflows/ci.yml"],
      "deploy_files": ["Dockerfile", "docker-compose.yml"],
      "gitignore": true,
      "gitattributes": false,
      "env_template": false,
      "branch_count": 3
    }
  }
}
```

### Field Descriptions

**Top-level fields** store the resolved values (from detection + user input):

| Field | Type | Values | Source |
|-------|------|--------|--------|
| `ci_provider` | string | Provider slug or `"none"` | Auto-detected or user-selected |
| `deploy_target` | string | Target slug or `"none"` | Auto-detected or user-selected |
| `commit_convention` | string | `"conventional"` or `"freeform"` | Auto-detected or user-selected |
| `environments` | string[] | Environment names | User-provided or inferred |

**`detected` sub-section** stores raw detection results for reference:

| Field | Type | Description |
|-------|------|-------------|
| `ci_files` | string[] | Paths of detected CI config files |
| `deploy_files` | string[] | Paths of detected deployment config files |
| `gitignore` | boolean | Whether `.gitignore` exists |
| `gitattributes` | boolean | Whether `.gitattributes` exists |
| `env_template` | boolean | Whether `.env.example` or `.env.template` exists |
| `branch_count` | number | Number of local git branches |

### Defaults

When a field is not detected and the user skipped the question or said "none for now":
```json
{
  "devops": {
    "ci_provider": "none",
    "deploy_target": "none",
    "commit_convention": "freeform",
    "environments": [],
    "detected": {
      "ci_files": [],
      "deploy_files": [],
      "gitignore": false,
      "gitattributes": false,
      "env_template": false,
      "branch_count": 0
    }
  }
}
```

## Downstream Consumers

How DevOps context stored in `config.json` is consumed by other agents.

### Researcher

Reads `devops.ci_provider` and `devops.deploy_target` to:
- Suggest stack-compatible solutions (e.g., recommend Vercel-optimized patterns if `deploy_target: "vercel"`)
- Avoid recommending incompatible tools (e.g., don't suggest Docker-only solutions if deploying to Vercel)
- Include CI-specific considerations in research (e.g., GitHub Actions caching strategies)

### Planner

Reads `devops.ci_provider` to:
- Include CI-aware tasks when plans modify dependencies or test config (e.g., "update CI config for new dependency")
- Add deployment verification tasks when relevant (e.g., "verify Docker build after API changes")
- Factor in CI constraints when estimating task complexity

### Health Check

Checks for DevOps gaps as part of the full check tier:
- Missing CI in projects with tests
- Missing `.gitignore` in any project
- Missing `.env.example` when env vars are referenced in code
- `Dockerfile` without `.dockerignore`
- Reports gaps as warnings with fix recommendations

### Codebase Mapper

Includes DevOps gaps in the CONCERNS.md "DevOps Gaps" section:
- Runs gap detection patterns from Section 4 during concerns exploration
- Each gap includes: Problem, Risk, Detection method, Recommendation
- Gaps feed into health check findings and roadmap suggestions

---

*Reference: devops-detection*
*Created: Phase 06-03*
*Consumers: new-project.md (Phase 5.7), map-codebase.md (concerns explorer), health-check.md*
