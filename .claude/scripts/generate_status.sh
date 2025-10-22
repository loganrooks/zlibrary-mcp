#!/usr/bin/env bash
# Generate STATUS.md from current git state and Serena memory
# Usage: bash .claude/scripts/generate_status.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATUS_FILE="$PROJECT_ROOT/.claude/STATUS.md"

# Get git info
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
RECENT_COMMITS=$(git log --oneline -5 2>/dev/null || echo "No commits")

# Check if .current-session exists (active session)
if [ -f "$PROJECT_ROOT/.current-session" ]; then
  SESSION_FILE=$(cat "$PROJECT_ROOT/.current-session")
  ACTIVE_SESSION="Yes"
  SESSION_NAME=$(basename "$SESSION_FILE" .md)

  # Extract objectives from session file
  OBJECTIVES=$(grep -A 10 "^## Objectives" "$SESSION_FILE" 2>/dev/null | tail -n +2 | head -10 || echo "No objectives found")
else
  ACTIVE_SESSION="No"
  SESSION_NAME="None"
  OBJECTIVES="No active session"
fi

# Extract current sprint from ROADMAP.md
CURRENT_SPRINT=$(grep -A 10 "^## Active Sprint" "$PROJECT_ROOT/.claude/ROADMAP.md" 2>/dev/null | grep "^- \[" | head -5 || echo "No roadmap found")

# Generate STATUS.md
cat > "$STATUS_FILE" <<EOF
# Current Status

**Last Updated**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
**Current Branch**: $CURRENT_BRANCH
**Active Session**: $ACTIVE_SESSION
**Generated from**: Git + Session notes

---

## Active Session

**Session**: $SESSION_NAME

### Objectives
$OBJECTIVES

---

## Current Sprint (from ROADMAP.md)

$CURRENT_SPRINT

---

## Recent Commits
\`\`\`
$RECENT_COMMITS
\`\`\`

---

## Quick Links

- [Current Roadmap](.claude/ROADMAP.md) - Strategic plan (1-3 weeks)
- [Architecture Overview](.claude/ARCHITECTURE.md) - System structure
- [Active Issues](../ISSUES.md) - All tracked issues
- [Development Standards](.claude/DEVELOPMENT_STANDARDS.md) - Coding standards

---

## Blockers

None currently.

---

*This file is auto-generated. Do not edit manually.*
*Source: Git + Session notes + ROADMAP.md*
*Update: \`bash .claude/scripts/generate_status.sh\`*
EOF

echo "✅ Generated $STATUS_FILE"
