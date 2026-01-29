---
phase: 01-integration-test-harness
plan: 02
subsystem: testing
tags: [docker, e2e, mcp-sdk, stdio]
dependency-graph:
  requires: [01-01]
  provides: [docker-e2e-test, full-stack-validation]
  affects: [02, 03]
tech-stack:
  added: []
  patterns: [stdio-client-transport, docker-test-container]
key-files:
  created:
    - Dockerfile.test
    - docker-compose.test.yml
    - __tests__/e2e/docker-mcp-e2e.test.js
  modified:
    - .dockerignore
    - package.json
decisions:
  - id: D-0102-01
    description: "Move lib/ COPY after uv sync to avoid setuptools package discovery conflicts"
    rationale: "setuptools scans working directory and finds lib/*.py as packages during zlibrary build"
metrics:
  duration: 4 min
  completed: 2026-01-29
---

# Phase 1 Plan 2: Docker E2E Test Summary

Docker-based E2E test using MCP SDK Client over StdioClientTransport to validate full stack (Node.js + Python + vendored zlibrary) in a clean container environment.

## What Was Done

### Task 1: Docker Infrastructure
- Created `Dockerfile.test` with node:20-slim, Python 3, UV, full build pipeline
- Created `docker-compose.test.yml` with environment variable passthrough
- Updated `.dockerignore` to allow test files through for test image builds

### Task 2: E2E Test and Scripts
- Created `__tests__/e2e/docker-mcp-e2e.test.js` with 3 test cases:
  - `listTools` verifies 11 tools with proper schemas
  - `callTool` with invalid tool verifies error handling
  - `get_download_limits` (live cred test) verifies structured response
- Added `test:e2e` and `test:e2e:local` npm scripts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] lib/ directory caused setuptools package discovery failure**
- Found during: Task 1 Docker build
- Issue: Copying lib/ before uv sync caused setuptools to find lib/*.py as packages during zlibrary editable install
- Fix: Moved lib/ COPY after uv sync step
- Commit: 38763fb

**2. [Rule 3 - Blocking] Missing scripts/ directory for postbuild validation**
- Found during: Task 1 Docker build
- Issue: npm run build runs postbuild which needs scripts/validate-python-bridge.js
- Fix: Added COPY scripts/ to Dockerfile.test
- Commit: 38763fb

## Verification

- Docker build: succeeds
- listTools: 11 tools found
- npm run test:e2e: 3/3 tests pass (including live credential test)

## Commits

| Commit | Description |
|--------|-------------|
| 38763fb | Docker test infrastructure (Dockerfile.test, compose, .dockerignore) |
| 5d0aefa | E2E test with MCP SDK Client and npm scripts |
