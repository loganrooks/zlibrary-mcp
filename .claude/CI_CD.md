# CI/CD Strategy & Implementation Guide

## Overview

This document outlines the Continuous Integration and Continuous Deployment (CI/CD) strategy for the Z-Library MCP project, including GitHub Actions workflows, quality gates, and deployment automation.

## CI/CD Philosophy

### Goals
1. **Automate Quality**: Catch issues before they reach production
2. **Fast Feedback**: Developers know immediately if something breaks
3. **Consistent Builds**: Same process everywhere (local, CI, production)
4. **Safe Deployments**: Automated testing prevents regressions
5. **Confidence**: Team can merge and deploy without fear

### Principles
- **Test Everything**: Every PR must pass all tests
- **Fail Fast**: Stop pipeline on first failure
- **Incremental Rollout**: Deploy to staging before production
- **Rollback Ready**: Can revert quickly if issues arise
- **Observable**: Track metrics for every deployment

## GitHub Actions Workflows

### Workflow: Continuous Integration

**File**: `.github/workflows/ci.yml`
**Triggers**: Push to any branch, Pull requests
**Purpose**: Validate code quality and functionality

```yaml
name: Continuous Integration

on:
  push:
    branches: ['**']
  pull_request:
    branches: [master, development]

jobs:
  quality-checks:
    name: Code Quality & Linting
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run Prettier check
        run: npm run format:check

      - name: Check TypeScript compilation
        run: npm run build

  test-nodejs:
    name: Node.js Tests
    runs-on: ubuntu-latest
    needs: quality-checks

    strategy:
      matrix:
        node-version: [18, 20]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests with coverage
        run: npm test

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          flags: nodejs

  test-python:
    name: Python Tests
    runs-on: ubuntu-latest
    needs: quality-checks

    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Create virtual environment
        run: python -m venv venv

      - name: Install dependencies
        run: |
          source venv/bin/activate
          pip install -r requirements.txt
          pip install -e ./zlibrary

      - name: Run pytest
        run: |
          source venv/bin/activate
          pytest --cov=lib --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: python

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [test-nodejs, test-python]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          npm ci
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pip install -e ./zlibrary

      - name: Build project
        run: npm run build

      - name: Run integration tests
        env:
          ZLIBRARY_EMAIL: ${{ secrets.ZLIBRARY_EMAIL_TEST }}
          ZLIBRARY_PASSWORD: ${{ secrets.ZLIBRARY_PASSWORD_TEST }}
        run: npm run test:integration

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Run npm audit
        run: npm audit --audit-level=moderate

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
```

### Workflow: Pull Request Validation

**File**: `.github/workflows/pr-validation.yml`
**Triggers**: Pull request opened/updated
**Purpose**: Enforce PR quality standards

```yaml
name: Pull Request Validation

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  validate-pr:
    name: Validate PR Requirements
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check PR title format
        uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          types: |
            feat
            fix
            docs
            style
            refactor
            perf
            test
            chore
            ci
            build
            revert

      - name: Check branch naming
        run: |
          BRANCH_NAME="${{ github.head_ref }}"
          if [[ ! $BRANCH_NAME =~ ^(feature|fix|hotfix|docs|refactor|test)/.+ ]]; then
            echo "❌ Branch name must start with feature/, fix/, hotfix/, docs/, refactor/, or test/"
            exit 1
          fi

      - name: Check for TODO/FIXME comments
        run: |
          if git diff origin/development...HEAD | grep -E "^\+.*TODO|^\+.*FIXME"; then
            echo "⚠️  Warning: New TODO/FIXME comments added"
          fi

      - name: Check file sizes
        run: |
          git diff --stat origin/development...HEAD | awk '{
            if ($3 ~ /\+/ && $1 > 1000) {
              print "⚠️  Large file change detected: " $1 " (" $3 " lines)"
              warning=1
            }
          }'

      - name: Enforce test coverage
        run: |
          npm ci
          npm test
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ Test coverage below 80%: $COVERAGE%"
            exit 1
          fi
          echo "✅ Test coverage: $COVERAGE%"

  size-check:
    name: Check Bundle Size
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Check bundle size
        run: |
          SIZE=$(du -sb dist/ | cut -f1)
          MAX_SIZE=10485760  # 10MB
          if [ $SIZE -gt $MAX_SIZE ]; then
            echo "❌ Bundle size exceeded: $SIZE bytes (max: $MAX_SIZE)"
            exit 1
          fi
          echo "✅ Bundle size: $SIZE bytes"
```

### Workflow: Release Automation

**File**: `.github/workflows/release.yml`
**Triggers**: Tag creation (v*)
**Purpose**: Automated releases with changelog

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    name: Build Release Artifacts
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          npm ci
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pip install -e ./zlibrary

      - name: Run tests
        run: |
          npm test
          source venv/bin/activate
          pytest

      - name: Build
        run: npm run build

      - name: Package release
        run: |
          mkdir -p release
          cp -r dist/ release/
          cp -r lib/ release/
          cp -r zlibrary/ release/
          cp package*.json release/
          cp requirements.txt release/
          cp README.md release/
          cp LICENSE release/
          tar -czf zlibrary-mcp-${{ github.ref_name }}.tar.gz release/

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-package
          path: zlibrary-mcp-${{ github.ref_name }}.tar.gz

  create-release:
    name: Create GitHub Release
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: release-package

      - name: Generate changelog
        id: changelog
        uses: metcalfc/changelog-generator@v4.1.0
        with:
          myToken: ${{ secrets.GITHUB_TOKEN }}

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          name: Release ${{ github.ref_name }}
          body: ${{ steps.changelog.outputs.changelog }}
          files: zlibrary-mcp-${{ github.ref_name }}.tar.gz
          draft: false
          prerelease: false

  publish-npm:
    name: Publish to npm
    needs: create-release
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v') && !contains(github.ref, '-')

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          registry-url: 'https://registry.npmjs.org'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Publish to npm
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Workflow: Dependency Updates

**File**: `.github/workflows/dependency-updates.yml`
**Triggers**: Schedule (weekly)
**Purpose**: Automated dependency updates

```yaml
name: Dependency Updates

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  update-dependencies:
    name: Update Dependencies
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Update npm dependencies
        run: |
          npm update
          npm audit fix --audit-level=moderate || true

      - name: Update Python dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install --upgrade pip
          pip list --outdated --format=json | \
            jq -r '.[] | .name' | \
            xargs -n1 pip install --upgrade || true
          pip freeze > requirements.txt

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'chore(deps): update dependencies'
          title: 'chore(deps): automated dependency updates'
          body: |
            Automated dependency update PR.

            Please review changes and ensure all tests pass before merging.
          branch: deps/automated-updates
          labels: dependencies, automated
```

## Quality Gates

### Required Checks for Merge

All PRs to `master` or `development` must pass:

1. ✅ **Linting**: ESLint + Prettier
2. ✅ **TypeScript Compilation**: No errors
3. ✅ **Unit Tests**: All passing, >80% coverage
4. ✅ **Integration Tests**: All passing
5. ✅ **Security Scan**: No high/critical vulnerabilities
6. ✅ **Code Review**: At least 1 approval
7. ✅ **Conventional Commits**: PR title follows format

### Branch Protection Configuration

**For `master`**:
- Require pull request before merging
- Require at least 1 approval
- Dismiss stale reviews on new commits
- Require status checks to pass:
  - `Code Quality & Linting`
  - `Node.js Tests`
  - `Python Tests`
  - `Integration Tests`
  - `Security Scanning`
- Require branches to be up to date
- Restrict push access (no direct commits)
- Restrict force pushes
- Restrict deletions

**For `development`**:
- Similar to master but:
  - Allow maintainers to bypass
  - Fewer required reviewers (can be 0 for small teams)

## Deployment Strategy

### Environment Structure

```
┌──────────────┐
│  Production  │  ← master branch
└──────────────┘
       ↑
       │ (manual approval)
       │
┌──────────────┐
│   Staging    │  ← development branch
└──────────────┘
       ↑
       │ (auto-deploy)
       │
┌──────────────┐
│    Feature   │  ← feature/* branches
└──────────────┘
```

### Deployment Workflow

**Feature Branches**:
- No deployment
- CI tests only

**Development Branch**:
- Auto-deploy to staging on merge
- Integration testing environment
- Team can test before production

**Master Branch**:
- Manual approval required
- Deploy to production
- Automatic rollback on failure

### Deployment Pipeline (Future)

```yaml
# .github/workflows/deploy.yml (example for future use)
name: Deploy to Production

on:
  push:
    branches: [master]

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://zlibrary-mcp.production.com

    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: npm run build

      - name: Deploy to server
        run: |
          # Deployment commands here
          # Could be Docker, SSH, cloud provider CLI, etc.

      - name: Health check
        run: |
          # Verify deployment succeeded
          curl -f https://zlibrary-mcp.production.com/health

      - name: Rollback on failure
        if: failure()
        run: |
          # Rollback commands
```

## Local Development CI

### Running CI Checks Locally

Before pushing, run these checks:

```bash
# Full CI simulation
npm run ci:local

# Individual checks
npm run lint          # Linting
npm run format:check  # Formatting
npm run build         # TypeScript compilation
npm test              # Tests with coverage
npm run test:integration  # Integration tests

# Python checks
source venv/bin/activate
pytest                # Python tests
pip check             # Dependency conflicts
```

### Pre-commit Hook Setup

Automate checks with git hooks:

```bash
# Install husky
npm install --save-dev husky
npx husky install

# Add pre-commit hook
npx husky add .husky/pre-commit "npm run ci:pre-commit"
```

**Pre-commit script** (in package.json):
```json
{
  "scripts": {
    "ci:pre-commit": "npm run lint && npm run build && npm test"
  }
}
```

## Monitoring & Observability

### Metrics to Track

1. **Build Metrics**:
   - Build duration
   - Success/failure rate
   - Flaky test detection

2. **Deployment Metrics**:
   - Deployment frequency
   - Mean time to production
   - Rollback frequency

3. **Quality Metrics**:
   - Test coverage trends
   - Code complexity
   - Security vulnerabilities

### Alerting

Configure alerts for:
- CI failures on master/development
- Security vulnerabilities detected
- Test coverage drop >5%
- Failed deployments
- Flaky tests (>3 retries needed)

### Status Badges

Add to README.md:

```markdown
[![CI](https://github.com/loganrooks/zlibrary-mcp/workflows/CI/badge.svg)](https://github.com/loganrooks/zlibrary-mcp/actions)
[![Coverage](https://codecov.io/gh/loganrooks/zlibrary-mcp/branch/master/graph/badge.svg)](https://codecov.io/gh/loganrooks/zlibrary-mcp)
[![npm version](https://badge.fury.io/js/zlibrary-mcp.svg)](https://badge.fury.io/js/zlibrary-mcp)
```

## Secrets Management

### Required Secrets

Configure in GitHub repository settings → Secrets and variables → Actions:

**Development/Testing**:
- `ZLIBRARY_EMAIL_TEST`: Test account email
- `ZLIBRARY_PASSWORD_TEST`: Test account password

**Deployment**:
- `NPM_TOKEN`: npm publishing
- `GITHUB_TOKEN`: Automatically provided

**Optional**:
- `SNYK_TOKEN`: Security scanning
- `CODECOV_TOKEN`: Coverage reporting
- `SLACK_WEBHOOK`: Deployment notifications

### Secret Rotation

- Rotate secrets quarterly
- Update immediately if compromised
- Use different secrets for prod/test
- Never log secrets in CI output

## Performance Optimization

### CI Speed Improvements

1. **Caching**:
   ```yaml
   - uses: actions/cache@v4
     with:
       path: |
         ~/.npm
         venv/
       key: ${{ runner.os }}-${{ hashFiles('**/package-lock.json', '**/requirements.txt') }}
   ```

2. **Parallel Jobs**:
   - Run Node.js and Python tests concurrently
   - Matrix builds for multiple versions

3. **Conditional Execution**:
   ```yaml
   - name: Run Python tests
     if: contains(github.event.head_commit.message, '[python]') || contains(github.event.head_commit.modified, 'lib/')
   ```

4. **Dependency Pruning**:
   - Use `npm ci` instead of `npm install`
   - Cache dependencies between runs

### Target Performance

- Total CI time: <5 minutes
- Test execution: <2 minutes
- Build time: <30 seconds
- Deployment: <3 minutes

## Troubleshooting

### Common CI Issues

**Issue**: Tests pass locally but fail in CI
**Solution**: Check environment differences (Node version, Python version, environment variables)

**Issue**: Slow CI builds
**Solution**: Enable caching, parallelize jobs, optimize test suite

**Issue**: Flaky tests
**Solution**: Identify with retry logic, fix race conditions, improve test isolation

**Issue**: Secrets not accessible
**Solution**: Verify secret names match, check repository permissions

### Debug Mode

Enable debug logging in GitHub Actions:

1. Repository Settings → Secrets → Actions
2. Add secret: `ACTIONS_STEP_DEBUG` = `true`
3. Add secret: `ACTIONS_RUNNER_DEBUG` = `true`

## Best Practices

### Do's

✅ **Keep CI Fast**: Optimize for speed to encourage frequent commits
✅ **Fail Fast**: Stop on first error to save resources
✅ **Cache Aggressively**: Cache dependencies, build artifacts
✅ **Test in Parallel**: Run independent tests concurrently
✅ **Monitor Trends**: Track build times, failure rates
✅ **Document Failures**: Add clear error messages
✅ **Use Matrix Builds**: Test multiple versions

### Don'ts

❌ **Don't Skip CI**: Never merge without passing checks
❌ **Don't Ignore Flaky Tests**: Fix or remove them
❌ **Don't Hardcode Secrets**: Use GitHub secrets
❌ **Don't Over-Engineer**: Start simple, add complexity as needed
❌ **Don't Ignore Slow Builds**: Optimize regularly
❌ **Don't Deploy Without Tests**: Always test before production

## Future Enhancements

### Planned Improvements

1. **Advanced Testing**:
   - Performance benchmarking
   - Visual regression testing
   - E2E tests with Playwright

2. **Deployment**:
   - Canary deployments
   - Blue-green deployment
   - Automatic rollback

3. **Monitoring**:
   - Real-time build monitoring
   - Slack/Discord notifications
   - Failure analytics

4. **Security**:
   - Container scanning
   - License compliance checking
   - SBOM generation

---

*This CI/CD guide should evolve with project needs. Update as new workflows are added or strategies change.*

**Last Updated**: 2025-09-30
**Version**: 1.0.0
**Maintained By**: Z-Library MCP Team
