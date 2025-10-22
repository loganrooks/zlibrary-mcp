Capture a lesson learned for continuous improvement: $ARGUMENTS

## Feedback Codification Loop

**Purpose**: Extract learning from mistakes/discoveries → Codify in standards → Future sessions learn automatically

### Actions

**Step 1: Capture Context**
```markdown
What happened: $ARGUMENTS

Prompt for details:
- What was the mistake/discovery?
- What was the user's feedback?
- What did we learn?
- How should this change our practices?
```

**Step 2: Write to Serena Memory**
```python
write_memory(f"lesson_{datetime.now().strftime('%Y%m%d_%H%M')}", {
  "timestamp": "...",
  "context": "$ARGUMENTS",
  "mistake": "{what went wrong}",
  "feedback": "{user's response}",
  "lesson": "{what we learned}",
  "pattern": "{extractable pattern if applicable}",
  "codifiedIn": "{where this is now documented}"
})
```

**Step 3: Determine If Codifiable**
```
Is this a generalizable pattern?
├─ Yes → Add to DEVELOPMENT_STANDARDS.md or PATTERNS.md
├─ Maybe → Add to META_LEARNING.md for review
└─ No → Keep in Serena memory only (specific context)
```

**Step 4: Update Documentation** (if pattern)
```bash
# Add to appropriate file
if [ -f ".claude/DEVELOPMENT_STANDARDS.md" ]; then
  # Add to anti-patterns section
  # OR add to best practices section
fi

# Always update META_LEARNING.md
echo "## $(date '+%Y-%m-%d'): {Topic}" >> .claude/META_LEARNING.md
echo "**Issue**: {what happened}" >> .claude/META_LEARNING.md
echo "**Lesson**: {what we learned}" >> .claude/META_LEARNING.md
echo "**Pattern**: {if extractable}" >> .claude/META_LEARNING.md
echo "**Codified**: {where documented}" >> .claude/META_LEARNING.md
echo "" >> .claude/META_LEARNING.md
```

### Expected Output

```
Lesson Captured: Fragile heuristics rejected by user

Context:
- Proposed regex pattern for X-mark text recovery
- User: "THIS IS TOO FRAGILE, only works for 0.1% of cases"

Analysis:
✅ Generalizable Pattern: Avoid fragile heuristics
✅ Added to: DEVELOPMENT_STANDARDS.md (Anti-Patterns section)
✅ Serena Memory: lesson_20251018_1430
✅ META_LEARNING.md: Entry created with context

Future Impact:
- AI will read this pattern in DEVELOPMENT_STANDARDS.md
- Will avoid similar fragile solutions
- User won't need to reject again

Self-Improvement Loop Complete ✅
```

## Usage

```bash
# After user provides critical feedback
/meta:capture-lesson "User rejected fragile regex heuristic for X-mark recovery"

# After discovering pattern
/meta:capture-lesson "Real PDF testing revealed architectural flaw missed by unit tests"

# After solving complex problem
/meta:capture-lesson "Span grouping essential to prevent malformed markdown from per-word formatting"
```

## Integration

Feeds into:
- META_LEARNING.md (monthly reflection source)
- DEVELOPMENT_STANDARDS.md (codified patterns)
- PATTERNS.md (code patterns)
- Serena memory (searchable history)

## Automation Trigger

**Suggested in**: META_LEARNING.md monthly reflection ritual

**Process**:
1. List all `lesson_*` memories from past month
2. Review for patterns
3. Codify generalizable patterns
4. Archive specific lessons

## See Also

- [META_LEARNING.md](../../META_LEARNING.md) - Learning repository
- [DEVELOPMENT_STANDARDS.md](../../DEVELOPMENT_STANDARDS.md) - Codified patterns
- Research: `claudedocs/research/claude-code-best-practices/findings.md`
