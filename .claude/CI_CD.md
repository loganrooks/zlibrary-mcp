<!-- Last Verified: 2026-02-01 -->

# CI/CD Infrastructure

## Overview

This project uses GitHub Actions for CI and Husky + lint-staged for local pre-commit quality gates.

## Pre-commit Hooks (Husky + lint-staged)

**How it works:** Running `git commit` triggers the `.husky/pre-commit` hook, which runs `npx lint-staged`.

**What lint-staged checks:**

| File Pattern | Action |
|-------------|--------|
| `*.ts`, `*.js` | `npm run build` (TypeScript compilation check) |
| `*.py` | `uv run ruff check --fix` + `uv run ruff format` |

**Why no tests in pre-commit:** Jest with ESM experimental modules is too slow for hooks. Full tests run in CI.

**Bypass:** `git commit --no-verify` (use sparingly).

**Setup:** Husky installs automatically via the `prepare` script on `npm install`.

## GitHub Actions CI Pipeline

**File:** `.github/workflows/ci.yml`

**Triggers:**
- Push to `master`
- Pull requests targeting `master`

### Jobs

#### `test`
Runs the full test suite:
1. Checkout code
2. Setup Node.js 18 + UV
3. `npm ci` + `uv sync` (install dependencies)
4. `npm run build` (TypeScript compilation)
5. `node --experimental-vm-modules node_modules/jest/bin/jest.js` (Node.js tests)
6. `uv run pytest` (Python tests)

#### `audit`
Runs security auditing:
1. Checkout code
2. Setup Node.js 18 + UV
3. `npm ci` + `uv sync`
4. `npm audit --omit=dev --audit-level=high` (Node.js dependency audit)
5. `uv run pip-audit || true` (Python dependency audit; `|| true` because vendored zlibrary fork may trigger false positives)

### Notes
- No Z-Library credentials in CI -- unit tests only
- Single Node 18 (LTS), no matrix build
- `npm audit` filters dev dependencies and only fails on high/critical

## Setup Script

**File:** `setup-uv.sh`

The setup script checks Python >= 3.10 before proceeding with UV installation. If the version is too old, it exits with an error message.

## Quality Gate Summary

| Gate | When | What |
|------|------|------|
| Pre-commit hook | `git commit` | Lint + type check on changed files |
| CI test job | Push/PR to master | Full test suite (Jest + pytest) |
| CI audit job | Push/PR to master | npm audit + pip-audit |
| Setup script | Initial setup | Python version >= 3.10 |
