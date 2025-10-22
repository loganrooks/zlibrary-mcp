#!/usr/bin/env bash
# Pre-commit quality validation hook
# Install: ln -s ../../.claude/hooks/pre-commit.sh .git/hooks/pre-commit

set -e  # Exit on first error

echo "🔍 Running pre-commit quality checks..."
echo ""

# 1. Check for temporary files in commit
echo "🧹 Checking for temporary files..."
if git diff --cached --name-only | grep -qE "temp|debug|/tmp/|\.pyc$"; then
  echo "⚠️  WARNING: Temporary files detected in commit:"
  git diff --cached --name-only | grep -E "temp|debug|/tmp/|\.pyc$"
  echo ""
  echo "Please remove temporary files before committing."
  exit 1
fi

# 2. Check documentation naming conventions
echo "📝 Validating documentation naming..."
if git diff --cached --name-only | grep -qE "^claudedocs/[^/]*[A-Z_]{3,}.*\.md$"; then
  echo "❌ ERROR: SCREAMING_CASE files in claudedocs/"
  git diff --cached --name-only | grep -E "^claudedocs/[^/]*[A-Z_]{3,}"
  echo ""
  echo "Use kebab-case naming per CLAUDE.md guidelines"
  echo "See: claudedocs/QUICK_REFERENCE.md"
  exit 1
fi

# 3. TypeScript compilation
if [ -f "package.json" ]; then
  echo "📦 Building TypeScript..."
  npm run build || {
    echo "❌ TypeScript compilation failed"
    exit 1
  }
fi

# 4. Python tests (fast unit tests, skip slow integration)
if [ -f ".venv/bin/pytest" ]; then
  echo "🧪 Running Python unit tests..."
  .venv/bin/pytest -x -m "not slow" --tb=short || {
    echo "❌ Python tests failed"
    exit 1
  }
fi

# 5. Real PDF tests (critical quality gate for RAG changes)
if git diff --cached --name-only | grep -qE "lib/rag_processing\.py|lib/.*detection\.py|lib/formatting"; then
  echo "🔬 Running real PDF validation tests (RAG changes detected)..."
  .venv/bin/pytest __tests__/python/test_real_world_validation.py -x || {
    echo "❌ Real PDF tests failed - RAG changes must pass validation"
    exit 1
  }
fi

# 6. Performance budget validation (if budgets changed or RAG modified)
if [ -f "test_files/performance_budgets.json" ]; then
  if git diff --cached --name-only | grep -qE "lib/rag|lib/.*detection|performance_budgets"; then
    echo "⚡ Validating performance budgets..."
    if [ -f "scripts/validation/validate_performance_budgets.py" ]; then
      .venv/bin/python scripts/validation/validate_performance_budgets.py || {
        echo "❌ Performance budget exceeded"
        exit 1
      }
    fi
  fi
fi

# 7. Check commit message format (conventional commits)
COMMIT_MSG_FILE="$1"
if [ -n "$COMMIT_MSG_FILE" ]; then
  COMMIT_MSG=$(cat "$COMMIT_MSG_FILE" 2>/dev/null || echo "")
  if ! echo "$COMMIT_MSG" | grep -qE "^(feat|fix|docs|chore|refactor|test|perf)(\(.+\))?:"; then
    echo "⚠️  WARNING: Commit message doesn't follow conventional commits format"
    echo "Expected: {type}({scope}): {description}"
    echo "Examples: feat(rag): ..., fix(tests): ..., docs(claude): ..."
    echo ""
    echo "See: .claude/VERSION_CONTROL.md for guidelines"
    # Warning only, don't block
  fi
fi

echo ""
echo "✅ All pre-commit checks passed!"
echo ""
