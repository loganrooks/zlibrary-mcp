Start a new development session: $ARGUMENTS

## Session Initialization Protocol

### Pre-Work Checklist
1. Load previous context from Serena memory
2. Check current branch and recent commits
3. Review ROADMAP.md for sprint priorities
4. Create session notes file with objectives

### Actions

**Step 1: Load Context**
```bash
# Check git status
git status
git branch --show-current
git log --oneline -5

# Load Serena memories
list_memories()
read_memory("current_plan")
read_memory("phase_2_status")  # Or current phase
read_memory("known_issues")
```

**Step 2: Create Session File**
```bash
# Create timestamped session notes
SESSION_FILE="claudedocs/session-notes/$(date +%Y-%m-%d-%H%M)-$ARGUMENTS.md"
echo "$SESSION_FILE" > .current-session

cat > "$SESSION_FILE" << 'EOF'
# Session: $ARGUMENTS

**Date**: $(date '+%Y-%m-%d %H:%M %Z')
**Branch**: $(git branch --show-current)

## Objectives
- [ ] {Extracted from ROADMAP.md or user input}
- [ ] {Additional objectives}

## Context
{From Serena memory: current_plan, blockers, recent decisions}

## Progress Log
### $(date '+%H:%M') - Session Start
- Loaded context from Serena memory
- Current sprint: {from ROADMAP.md}

EOF
```

**Step 3: Orient**
```bash
# Display session context
echo "📋 Session Started: $ARGUMENTS"
echo "📍 Branch: $(git branch --show-current)"
echo "🎯 Sprint Focus: {from ROADMAP.md Active Sprint}"
echo "⚠️ Known Issues: {count from Serena memory}"
echo ""
echo "✅ Session file created: $SESSION_FILE"
echo "💡 Use /project:session-update to log progress"
```

### Expected Output

```
Session Started: rag-formatting-implementation

Context Loaded:
- Current Plan: Phase 2 - RAG Pipeline Quality
- Active Sprint: Formatting preservation, Performance budgets
- Known Blockers: 0
- Recent Decisions: 2 (Stage 2 independence, TDD workflow)

📝 Session file: claudedocs/session-notes/2025-10-21-1430-rag-formatting-implementation.md

Next Steps:
1. Review ROADMAP.md for today's priorities
2. Check ARCHITECTURE.md for current system state
3. Begin work with clear objectives

Use /project:session-update "{progress}" to log milestones
```

## Usage

```bash
# Start new session
/project:session-start "feature-name-or-task"

# Example
/project:session-start "sous-rature-detection-validation"
```

## Integration

This command creates `.current-session` file that points to active session notes.
Other commands (`session-update`, `session-end`) read this file to know which session is active.

## See Also

- `/project:session-update` - Log progress during session
- `/project:session-end` - Complete and summarize session
- `/sc:load` - Load session state from Serena (alternative/complement)
