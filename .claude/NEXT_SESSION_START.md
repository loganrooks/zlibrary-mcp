# Quick Start for Next Session

**Last Updated**: 2025-10-21
**Purpose**: Fast initialization instructions for fresh AI agent

---

## 🚀 Initialization Protocol (Choose Your Speed)

### ⚡ Fast Track (10 minutes)

**Read these 3 files IN ORDER**:

1. **`.claude/ROADMAP.md`** (3 min)
   - Shows current sprint priorities
   - Checkbox status = what's done/pending
   - **Purpose**: Know what to work on

2. **`.claude/ARCHITECTURE.md`** (5 min)
   - System components and status
   - Phase 2: 85% complete
   - **Purpose**: Understand what's built

3. **`claudedocs/session-notes/2025-10-21-system-improvements-complete.md`** (2 min)
   - Last session accomplishments
   - Current state summary
   - **Purpose**: Know what just happened

**Then load Serena**:
```
list_memories()
read_memory("session_2025_10_21_complete")
```

**Result**: Ready to continue development in ~10 minutes

---

### 📚 Complete Context (20 minutes)

**Follow essential reading order from CLAUDE.md** (items 1-6):
1. PROJECT_CONTEXT.md - Mission and domain
2. ROADMAP.md - Strategic plan ⭐
3. ARCHITECTURE.md - System structure ⭐
4. ISSUES.md - Known problems
5. IMPLEMENTATION_ROADMAP.md - Action plan
6. Latest session notes ⭐

**Then load Serena memories**:
```
read_memory("session_2025_10_21_complete")
read_memory("system_improvements_2025_10_21")
read_memory("workspace_organization_2025_10_21")
```

**Result**: Fully oriented with complete context

---

## 🎯 Current State (TL;DR)

**Branch**: `feature/rag-pipeline-enhancements-v2`

**Just Completed** (2025-10-21):
- ✅ Formatting preservation (*italic*, **bold**, ~~strikethrough~~)
- ✅ Workspace reorganized (52 files → professional hierarchy)
- ✅ System framework (ROADMAP, ARCHITECTURE, standards, commands)
- ✅ Autonomous learning specification

**Test Status**: 49/49 passing (100%)

**Next Direction** (choose one):
- **Option A**: Implement Phase 2 autonomous features (logging, triggers, automation)
- **Option B**: Continue Week 2 RAG features (marginalia, citations, footnotes)
- **Option C**: ML recovery research (text under X-marks)

---

## 💡 What to Say to Fresh Agent

### Minimal Instruction
```
"Read .claude/ROADMAP.md and .claude/ARCHITECTURE.md,
then load Serena memory 'session_2025_10_21_complete'.
Check claudedocs/session-notes/2025-10-21-system-improvements-complete.md
for what we just accomplished."
```

### Complete Instruction
```
"Follow the essential reading order in CLAUDE.md (the first 6 items).
The most important new additions are:
- .claude/ROADMAP.md (#2) - shows current sprint
- .claude/ARCHITECTURE.md (#3) - shows system state
- Session notes from 2025-10-21 (#6) - last session context

Then use Serena to load session state:
  list_memories()
  read_memory('session_2025_10_21_complete')

This will give you full context in about 20 minutes of reading."
```

### If Resuming Specific Task
```
"We're working on {task_name}.

Quick context:
1. Read .claude/ROADMAP.md (item #{priority} in current sprint)
2. Read .claude/ARCHITECTURE.md (understand system)
3. Read docs/specifications/{SPEC}.md (if exists)
4. Read .claude/TDD_WORKFLOW.md (for RAG features)
5. Load Serena: read_memory('session_2025_10_21_complete')

Then continue from where we left off."
```

---

## 📋 Key New Documents (Created This Session)

**Framework** (must-read for system understanding):
- `.claude/ROADMAP.md` ⭐ Strategic planning (1-3 weeks)
- `.claude/ARCHITECTURE.md` ⭐ System structure (components, ADRs, status)
- `.claude/DEVELOPMENT_STANDARDS.md` - Coding standards and anti-patterns
- `.claude/AUTONOMOUS_LEARNING_SYSTEM.md` - Self-improvement specification

**Automation** (how the system helps):
- `.claude/commands/project/session-*.md` (3 commands)
- `.claude/hooks/pre-commit.sh` - Quality gates
- `.claude/scripts/generate_status.sh` - Status generation

**Documentation** (for reference):
- `claudedocs/QUICK_REFERENCE.md` - Where to document what
- `claudedocs/session-notes/2025-10-21-system-improvements-complete.md` - Session summary
- `claudedocs/research/claude-code-best-practices/findings.md` - Research (51KB)

---

## ⚙️ Available Commands (New!)

**Session Lifecycle**:
- `/project:session-start "{topic}"` - Initialize new session
- `/project:session-update "{progress}"` - Log progress
- `/project:session-end` - Complete and summarize

**Meta-Learning**:
- `/meta:capture-lesson "{insight}"` - Codify learning

**Existing**:
- `/sc:load` - Load from Serena (alternative to session-start)
- `/sc:save` - Save to Serena (alternative to session-end)

---

## 🧭 Navigation

**Always Current**:
- ROADMAP.md - What we're building
- ARCHITECTURE.md - How it's built
- STATUS.md - Where we are (auto-generated)

**Reference**:
- DOCUMENTATION_MAP.md - Central hub for all docs
- claudedocs/README.md - claudedocs navigation
- docs/adr/README.md - All architecture decisions

---

## ✅ Success Checklist

After reading, you should be able to answer:
- [ ] What's the current sprint priority? (from ROADMAP.md)
- [ ] What's the system architecture? (from ARCHITECTURE.md)
- [ ] What was just accomplished? (from session notes)
- [ ] What should I work on next? (from ROADMAP + user choice)
- [ ] Where are the standards? (DEVELOPMENT_STANDARDS.md)

If you can answer all 5, you're ready to work! 🚀

---

**File Location**: Keep this in `.claude/NEXT_SESSION_START.md` for easy reference
