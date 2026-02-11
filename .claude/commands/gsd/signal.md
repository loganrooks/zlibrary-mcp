---
name: gsd:signal
description: Log a manual signal observation to the knowledge base with context from the current conversation
argument-hint: '"description" [--severity critical|notable] [--type deviation|struggle|config-mismatch|custom]'
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

<objective>
Create a manual signal entry in the knowledge base capturing an observation from the current conversation.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/signal.md
@./.claude/get-shit-done/references/signal-detection.md
@.claude/agents/knowledge-store.md
@.claude/agents/kb-templates/signal.md
</execution_context>

<context>
Arguments: $ARGUMENTS

@.planning/STATE.md
@.planning/config.json
</context>

<process>
Execute the signal workflow from @./.claude/get-shit-done/workflows/signal.md end-to-end.

Pass inline arguments to the workflow for parsing. The workflow handles:
- Argument parsing and missing field collection
- Conversation context extraction and frustration detection
- Signal preview and user confirmation
- Deduplication checking and cap enforcement
- Signal file creation and index rebuild
- Conditional git commit
</process>
