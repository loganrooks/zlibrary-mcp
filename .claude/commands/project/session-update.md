Update the current session with progress: $ARGUMENTS

## Session Progress Logging

### Actions

**Step 1: Find Active Session**
```bash
# Read active session file path
if [ ! -f .current-session ]; then
  echo "❌ No active session. Start one with /project:session-start"
  exit 1
fi

SESSION_FILE=$(cat .current-session)
```

**Step 2: Append Progress Entry**
```bash
# Append timestamped update to Progress Log section
TIMESTAMP=$(date '+%H:%M')

echo "" >> "$SESSION_FILE"
echo "### $TIMESTAMP - $ARGUMENTS" >> "$SESSION_FILE"

# Optionally add context from TodoWrite state
# {automated: list completed todos since last update}
```

**Step 3: Update Checkboxes** (if milestone reached)
```bash
# If $ARGUMENTS contains keywords like "completed", "finished", "done"
# Update objective checkboxes in session file
# sed -i 's/- \[ \] {matching objective}/- [x] {matching objective}/' "$SESSION_FILE"
```

**Step 4: Update STATUS.md** (optional)
```bash
# Regenerate STATUS.md with latest progress
# bash .claude/scripts/generate_status.sh
```

### Expected Output

```
✅ Session updated: 14:45 - Completed span grouping logic, tests passing

Progress logged to: claudedocs/session-notes/2025-10-21-1430-rag-formatting.md

Current session state:
- Objectives: 2/4 completed
- Time elapsed: 2h 15m
- Next: Integration with rag_processing.py
```

## Usage

```bash
# Log progress
/project:session-update "Completed unit tests, 40/40 passing"

# Log milestone
/project:session-update "✅ Formatting preservation implemented and validated"

# Log blocker
/project:session-update "⚠️ BLOCKER: OCR cannot read through heavy X-marks, needs ML"
```

## Auto-Detection

If update contains:
- "✅" or "completed" or "done" → Mark objective as complete
- "⚠️" or "blocker" or "blocked" → Add to blockers section
- "❌" or "failed" or "error" → Flag for review

## Integration

Works with:
- `session-start` (creates session file)
- `session-end` (uses progress log for summary)
- Serena memory (updates can trigger memory writes)
- STATUS.md (auto-regenerates on updates)

## See Also

- `/project:session-start` - Initialize session
- `/project:session-end` - Complete and summarize
- `/sc:save` - Persist to Serena memory
