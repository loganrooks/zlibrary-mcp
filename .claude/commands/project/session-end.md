End the current session with summary generation.

## Session Completion Protocol

### Actions

**Step 1: Find Active Session**
```bash
if [ ! -f .current-session ]; then
  echo "❌ No active session to end"
  exit 1
fi

SESSION_FILE=$(cat .current-session)
```

**Step 2: Generate Summary**
```bash
# Calculate session duration
START_TIME=$(grep "Session Start" "$SESSION_FILE" | head -1 | awk '{print $5}')
END_TIME=$(date '+%H:%M')

# Extract accomplishments from progress log
ACCOMPLISHMENTS=$(grep "^### [0-9]" "$SESSION_FILE" | sed 's/^### [0-9:]* - /- /')

# Get git changes
GIT_CHANGES=$(git diff --stat HEAD~1..HEAD 2>/dev/null || echo "No commits this session")

# Identify uncompleted objectives
PENDING=$(grep "^- \[ \]" "$SESSION_FILE" || echo "All objectives completed!")

# Generate summary section
cat >> "$SESSION_FILE" << EOF

---

## Session Summary

**Duration**: $START_TIME - $END_TIME
**Branch**: $(git branch --show-current)

### Accomplishments
$ACCOMPLISHMENTS

### Git Changes
\`\`\`
$GIT_CHANGES
\`\`\`

### Pending Items
$PENDING

### Lessons Learned
{Prompt user or extract from progress log}

### Next Session Actions
{From pending objectives + new insights}

---

**Session completed**: $(date '+%Y-%m-%d %H:%M %Z')
EOF
```

**Step 3: Update Serena Memory**
```python
# Save session summary to Serena
write_memory(f"session_summary_{datetime.now().strftime('%Y%m%d_%H%M')}", {
  "sessionFile": SESSION_FILE,
  "duration": "...",
  "accomplishments": [...],
  "pendingItems": [...],
  "lessonsLearned": [...],
  "nextActions": [...]
})

# Update current_session memory to null (session ended)
write_memory("current_session", None)
```

**Step 4: Update STATUS.md**
```bash
# Clear active task (session ended)
bash .claude/scripts/generate_status.sh
```

**Step 5: Cleanup**
```bash
# Remove .current-session marker
rm .current-session

# Clean temporary files
rm -f /tmp/*.png /tmp/debug_* /tmp/test_*.py 2>/dev/null

echo "✅ Session ended and summarized"
echo "📝 Summary saved to: $SESSION_FILE"
echo "💾 State persisted in Serena memory"
```

### Expected Output

```
Session Summary Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration: 14:30 - 17:45 (3h 15m)
Branch: feature/rag-pipeline-enhancements-v2

Accomplishments:
- ✅ Implemented span grouping logic (40 tests passing)
- ✅ Validated with real Derrida PDF
- ✅ Fixed Stage 2 test regressions
- ✅ Committed formatting implementation (2,650 lines)

Git Changes:
  9 files changed, 2650 insertions(+), 44 deletions(-)

Pending:
- [ ] ML-based text recovery research
- [ ] Expand test corpus (3-5 more PDFs)

Lessons Learned:
- OCR cannot read through heavy X-marks, needs ML approach
- Span grouping essential for proper markdown formatting

Next Session:
1. Review ISSUES.md for Phase 2 completion status
2. Consider Week 2 features (marginalia, citations)
3. OR pursue ML recovery research

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Session summary saved to: claudedocs/session-notes/2025-10-21-1430-rag-formatting.md
💾 State persisted in Serena memory
🧹 Temporary files cleaned

Resume next session with: /project:session-start "{topic}"
```

## Usage

```bash
# End current session
/project:session-end

# AI will guide you through summary generation
# May prompt for lessons learned or next actions
```

## Integration

Completes the session lifecycle:
- `session-start` → `session-update` (n times) → `session-end`
- Integrates with Serena memory persistence
- Generates human-readable summaries
- Cleanup automation

## See Also

- `/project:session-start` - Initialize session
- `/project:session-update` - Log progress
- `/sc:save` - Alternative Serena persistence
- [SESSION_STATE_SYSTEM.md](../../SESSION_STATE_SYSTEM.md) - Complete design
