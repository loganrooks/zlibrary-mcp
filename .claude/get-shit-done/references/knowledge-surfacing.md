# Knowledge Surfacing Reference

Reference specification for how agents query, rank, cite, and propagate knowledge from the GSD Knowledge Store. This document is consumed by all agent types via `@get-shit-done/references/knowledge-surfacing.md` references in their `<knowledge_surfacing>` sections.

**Version:** 1.0.0
**Phase:** 05-knowledge-surfacing

---

## 1. Overview

Knowledge surfacing makes passive knowledge (lessons and spike decisions stored in `./.claude/gsd-knowledge/`) active by instructing agents to query and apply it during their workflows.

**Scope:** Lessons (from reflection) and spike decisions only. Raw signals are NOT surfaced -- they are unprocessed noise. The reflection engine distills signals into lessons; agents consume the distilled form.

**Mechanism:** Agent-initiated (pull-based). Agents explicitly query the knowledge base using Read/Grep on KB paths. No auto-injection into agent prompts. Agent prompt sections include instructions on when and how to query.

**Fork compatibility:** Agents check if this file exists before applying knowledge surfacing instructions. If `get-shit-done/references/knowledge-surfacing.md` does not exist (upstream GSD without the reflect fork), agents skip knowledge surfacing entirely.

```bash
# Fork detection pattern (used in agent <knowledge_surfacing> sections)
if [ -f "get-shit-done/references/knowledge-surfacing.md" ]; then
  # Apply knowledge surfacing
else
  # Skip -- upstream GSD without reflect fork
fi
```

---

## 2. Query Mechanics

Agents query the knowledge base by reading the index file and then selectively reading full entry files.

### 2.1 Step-by-Step Query Process

1. **Read the KB index:**
   ```bash
   cat ./.claude/gsd-knowledge/index.md
   ```
   The index contains all active entries across all projects, organized by type (Signals, Spikes, Lessons).

2. **Scan relevant tables:**
   - Scan the **Lessons** table for entries whose tags overlap with the current work context (technology domain, goal keywords, libraries, patterns)
   - Scan the **Spikes** table for entries whose tags match current research questions or technology decisions

3. **Select top matches (max 5):**
   Use LLM judgment to pick the most relevant entries based on tag overlap, project relevance, and category alignment. Do NOT rely on brittle tag-counting -- semantic relevance matters more.

4. **Read full entry files:**
   ```bash
   cat ./.claude/gsd-knowledge/lessons/{category}/{lesson-name}.md
   cat ./.claude/gsd-knowledge/spikes/{project}/{spike-name}.md
   ```

5. **Check freshness** (see Section 4)

6. **Apply to current work** with inline citations (see Section 6)

### 2.2 Index Format Reference

The KB index at `./.claude/gsd-knowledge/index.md` has this structure:

```markdown
# Knowledge Store Index

**Generated:** 2026-02-02T15:00:00Z
**Total entries:** 47

## Lessons (12)

| ID | Project | Category | Tags | Date | Status |
|----|---------|----------|------|------|--------|
| les-2026-02-02-validate-tokens | _global | architecture | auth, oauth, jwt | 2026-02-02 | active |

## Spikes (12)

| ID | Project | Outcome | Tags | Date | Status |
|----|---------|---------|------|------|--------|
| spk-2026-01-28-jwt-refresh-strategy | my-app | confirmed | auth, jwt | 2026-01-28 | active |
```

**Query by tag:** Grep for tag keywords in the Tags column.
**Query by project:** Filter Project column for current project name or `_global`.
**Query by type:** Read the relevant section (Lessons, Spikes).

### 2.3 Cross-Project Querying (SURF-04)

Cross-project knowledge surfacing is architecturally built-in. The index contains ALL entries across all projects. Lessons are organized by category, not project.

To get cross-project results: query index.md **without** filtering by project name. Global lessons (`_global`) plus lessons from all projects are all visible in the index.

To get project-specific results: filter the Project column for the current project name or `_global`.

Default behavior: agents query without project filter to surface all potentially relevant knowledge, regardless of originating project.

---

## 3. Relevance Matching

### 3.1 Matching Strategy

Hybrid: index file + tags. Agents read index one-liner summaries first, then fetch relevant entries.

### 3.2 Tag Format

Hierarchical freeform tags with no fixed vocabulary. Nesting is encouraged:
- `auth/jwt`, `auth/oauth`, `auth/sessions`
- `database/prisma/migrations`, `database/postgres`
- `testing/vitest`, `testing/fixtures`

Grep handles partial matching naturally -- `grep "auth"` catches both `auth` and `auth/jwt`.

### 3.3 Stack Awareness

Agents include relevant technologies in their query context. No magical auto-boost -- the agent prompt instructs them to consider the current stack (from package.json, CONTEXT.md, RESEARCH.md) when assessing relevance.

### 3.4 Partial Matches

Include with lower rank. A lesson about "React performance" is still potentially useful when researching "React state management." Agents use judgment to assess partial relevance.

### 3.5 Ranking Method

Agent LLM judgment. The agent reads one-liner summaries from the index and ranks by semantic relevance to the current query. Tag overlap count is brittle -- LLMs are better at contextual relevance assessment.

### 3.6 Conflicting Entries

Surface both, flag the conflict. The agent resolves with full context of the current situation. Auto-preferring by recency or confidence is too blunt -- the older entry may be more applicable to the current case.

### 3.7 Cross-Domain Entries

An entry tagged `auth + database` appears when querying `auth` alone. It ranks higher when the query touches both domains.

---

## 4. Freshness Checking (depends_on)

### 4.1 Primary Mechanism: depends_on

Knowledge entries may include a `depends_on` field in frontmatter:

```yaml
depends_on:
  - "prisma >= 4.0"
  - "src/lib/auth.ts exists"
  - "NOT monorepo"
```

The `depends_on` field is a documentation field -- agents READ it and use judgment to assess whether conditions still hold. This is NOT an automated verification system.

**Checking process:**
1. Read `depends_on` from entry frontmatter
2. Use judgment to assess whether dependencies still hold:
   - Library version: check package.json if accessible
   - File existence: check if file still exists
   - Negation: check if condition is still false
3. If dependencies hold: entry is fresh, apply normally
4. If dependencies changed: surface with caveat noting the change
   - Example: "Note: [les-2026-01-15-validate-tokens] depends on Prisma 4.x; current project uses Prisma 5.x -- may need re-evaluation"

### 4.2 Temporal Decay Fallback

When `depends_on` is absent or unverifiable, fall back to temporal decay heuristics:

| Entry Age | Confidence | Treatment |
|-----------|------------|-----------|
| < 30 days | Full confidence | Apply normally |
| 30-90 days | Slight reduction | Apply with minor age note |
| > 90 days | Lower confidence | Apply with age caveat, lower ranking |

**Critical rule:** Never exclude an entry solely based on age. Old knowledge may still be perfectly valid. Surface with caveat rather than suppress.

### 4.3 Failed Phase Knowledge

Include entries from failed or abandoned phases, flagged as such. "We tried X and it failed" is valuable knowledge -- it prevents repeating failed approaches.

---

## 5. Token Budget and Truncation

### 5.1 Budget

**Soft cap:** ~500 tokens of surfaced knowledge. Agents can exceed if knowledge is genuinely critical, but this prevents context flooding.

**Executor exception:** ~200 tokens (deviation context only). Executors have a tighter budget because they only surface knowledge during auto-fix deviations.

### 5.2 Token Estimation

Rough estimation: ~1 token per 4 characters. This is adequate for a soft cap -- exact counting is unnecessary when agents can exceed the cap for critical knowledge.

### 5.3 Truncation Strategy

When surfaced knowledge exceeds the budget:

1. **First pass:** Trim all entries to one-liner summaries (preserves breadth over depth)
2. **Second pass:** If still over budget, drop lowest-relevance entries
3. **Exception:** Agent can exceed budget and note it if knowledge is genuinely critical to the current task

---

## 6. Citation Format and Output

### 6.1 Inline Citations

Use entry IDs in natural language -- grepable and readable:

```
A prior lesson [les-2026-01-15-validate-tokens] found that refresh tokens must be validated server-side.
```

```
Per spike [spk-2026-01-20-jwt-refresh-strategy], JWT refresh with rotation is the recommended approach.
```

### 6.2 Knowledge Applied Summary Section

Include at the end of agent output:

```markdown
## Knowledge Applied

**KB entries consulted:** 3 lessons, 1 spike
**Applied:**
- [les-2026-01-15-validate-tokens]: Informed auth approach selection
- [spk-2026-01-20-jwt-refresh-strategy]: Prior spike confirms JWT refresh viable

**Dismissed:**
- [les-2026-01-10-avoid-barrel-exports]: Not relevant to current phase

**Spikes avoided:** 1 (spk-2026-01-20-jwt-refresh-strategy)
```

### 6.3 No Results

When no relevant entries are found:

```markdown
## Knowledge Applied

Checked knowledge base, no relevant entries found.
```

### 6.4 Verbosity

Summary + file path link to full entry. Agents show the conclusion/recommendation with a path to the full entry file. Consuming agents can drill down if they need full rationale.

---

## 7. Spike Deduplication (SPKE-08)

Spike deduplication is part of the mandatory initial KB query -- not a separate step.

### 7.1 Detection Process

During the initial KB query:

1. Read the **Spikes** table in `./.claude/gsd-knowledge/index.md`
2. For each spike entry, check if:
   - Tags overlap with current research question or technology
   - Hypothesis is similar to current question
3. If a matching spike is found, read the full spike entry

### 7.2 Matching Criteria

A prior spike applies when:
- **Same technology** (e.g., both about JWT refresh)
- **Same constraints** (e.g., same framework, same scale requirements)
- **Same scale** (e.g., both targeting similar user counts)
- **No significant codebase changes** that would invalidate the finding (check `depends_on`)

### 7.3 Adopting Spike Results

**Full match:** Adopt the finding, cite it, note as "spike avoided."
```
Per spike [spk-2026-01-20-jwt-refresh], JWT refresh with rotation is the recommended approach -- same tech stack and constraints apply.
```

**Partial match:** Adopt the answered portion, note the gap that still needs investigation.
```
Spike [spk-2026-01-20-jwt-refresh] confirms JWT refresh viability, but didn't test with our specific auth provider. Gap: provider-specific token format.
```

### 7.4 Confidence Levels

Surface the spike's confidence level:
- **confirmed/rejected:** High confidence -- adopt unless `depends_on` flags indicate staleness
- **partial:** Medium confidence -- adopt answered portion, note limitations
- **inconclusive:** Low confidence -- surface as reference, do not adopt blindly

### 7.5 Composite Answers

When multiple spikes together answer a question: synthesize from all applicable spikes, but flag as composite.
```
Composite from [spk-001] and [spk-002] -- not directly tested as a unit.
```

### 7.6 Incidental Answers

When a spike incidentally answered the current question (different primary hypothesis): adopt with lower confidence, noting it was not the spike's primary focus.

### 7.7 End-of-Research Stat

At the end of research output, include:
```
Spikes avoided: N (spk-xxx, spk-yyy)
```

---

## 8. Agent-Specific Behavior

| Agent | Trigger | Query Type | Priority | Budget |
|-------|---------|------------|----------|--------|
| Phase researcher | Mandatory at start + on error/direction change | Full KB (lessons + spikes) | Spike decisions first | ~500 tokens |
| Planner | Optional, at discretion | Lessons only | Strategic lessons | ~500 tokens |
| Debugger | Optional, at discretion | Lessons + spikes related to error | Both equally | ~500 tokens |
| Executor | ONLY on deviation Rules 1-3 | Lessons related to error | Error-relevant | ~200 tokens |

### 8.1 Phase Researcher

**Mandatory initial check** before beginning external research:
1. Read `./.claude/gsd-knowledge/index.md`
2. Scan Lessons and Spikes tables for tag overlap with phase technology domain, goal keywords, and specific libraries from CONTEXT.md
3. For matching entries (max 5), read full entry files
4. Check spike deduplication (Section 7)
5. Incorporate relevant findings into RESEARCH.md
6. Include "Knowledge Applied" section

**Re-query:** On unexpected errors or direction changes during research.

### 8.2 Planner

**Optional querying** at the planner's discretion. Useful when:
- Making technology choices that past lessons may inform
- Structuring tasks where past patterns suggest pitfalls
- Planning for areas where prior spikes resolved uncertainty

Queries lessons only (not spikes -- those should already be in RESEARCH.md from the researcher).

### 8.3 Debugger

**Optional querying** at the debugger's discretion. Useful when:
- Investigating errors that may have occurred before
- Debugging issues in technology areas with known quirks

Queries both lessons and spikes equally -- prior experiments and distilled wisdom are both relevant for debugging.

### 8.4 Executor

**ONLY on deviation (Rules 1-3).** When the executor enters an auto-fix path:
1. Before fixing, check KB for similar past issues:
   ```bash
   grep -i "{error-keyword}" ./.claude/gsd-knowledge/index.md
   grep -i "{technology}" ./.claude/gsd-knowledge/index.md
   ```
2. If matching entry exists, read it and apply to the fix
3. Cite in deviation tracking:
   ```
   [Rule 1 - Bug] Fixed auth token refresh (informed by [les-2026-01-15-validate-tokens])
   ```

**Do NOT query KB:** At plan start, before each task, during normal execution, or when applying Rule 4 (architectural deviation -- checkpoint to user instead).

---

## 9. Knowledge Chain (Downstream Propagation)

### 9.1 Propagation Model

Upstream agents write their KB findings to existing artifacts (RESEARCH.md, PLAN.md). Downstream agents see upstream findings naturally through the standard artifact reading flow:

```
Researcher queries KB
       |
       v
Findings written to RESEARCH.md
       |
       v
Planner reads RESEARCH.md (includes KB findings)
       |
       v
Plan decisions written to PLAN.md
       |
       v
Executor reads PLAN.md (includes KB-informed decisions)
```

### 9.2 Downstream Supplementation

Downstream agents CAN query the KB for additional knowledge relevant to their specific concerns. The researcher's query covers broad relevance; downstream agents may need knowledge specific to their narrower task.

### 9.3 Propagation Form

Upstream agents propagate their interpretation (conclusion, not raw entry). Downstream agents receive: "Researcher found that approach X failed per [les-003], recommending Y instead." If they need the original entry, they can query directly.

---

## 10. Progressive Disclosure

### 10.1 Two-Tier Model

The knowledge store already has progressive disclosure built in:

- **Tier 1: Index summaries** (`./.claude/gsd-knowledge/index.md`) -- one-line entry per knowledge item with ID, tags, date, and status. Always read first.
- **Tier 2: Full entry files** (individual `.md` files) -- complete frontmatter, context, recommendations, evidence. Read on-demand for top matches only.

### 10.2 Agent Flow

For v1, agents use the simpler approach:
1. Read index (Tier 1)
2. Pick top matches by LLM judgment
3. Read full entries for those matches (Tier 2)

No interactive menu or formal drill-in protocol. The two-tier model is applied naturally by reading the index first and selectively reading full entries.

---

## 11. Debug Mode

### 11.1 Configuration

Flag: `knowledge_debug` in `.planning/config.json` (default: `false`).

**Checking the config:**
```bash
KNOWLEDGE_DEBUG=$(cat .planning/config.json 2>/dev/null | grep -o '"knowledge_debug"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o 'true\|false' || echo "false")
```

### 11.2 When Enabled (knowledge_debug: true)

Agents include a **"## KB Debug Log"** section listing ALL entries they considered from index.md:

```markdown
## KB Debug Log

| ID | Tags | Relevance | Freshness | Action |
|----|------|-----------|-----------|--------|
| les-2026-01-15-validate-tokens | auth, jwt | HIGH -- direct tag match | Fresh (depends_on holds) | Applied |
| les-2026-01-10-avoid-barrel-exports | architecture, imports | LOW -- no domain overlap | Fresh | Excluded |
| spk-2026-01-20-jwt-refresh | auth, jwt | HIGH -- same technology | Fresh | Applied (spike avoided) |
```

This section is in addition to the standard "## Knowledge Applied" section.

### 11.3 When Disabled (knowledge_debug: false)

Standard behavior: only the "## Knowledge Applied" section with applied and dismissed entries. No debug logging overhead.

---

*Reference version: 1.0.0*
*Created: 2026-02-07*
*Phase: 05-knowledge-surfacing, Plan: 01*
