---
id: sig-2026-03-11-gsd-hooks-esm-commonjs-conflict
type: signal
project: zlibrary-mcp
tags: [gsd-hooks, esm, commonjs, package-json, node-modules]
created: 2026-03-11T00:00:00Z
updated: 2026-03-11T00:00:00Z
durability: convention
status: active
severity: notable
signal_type: config-mismatch
phase: 14
plan:
polarity: negative
source: manual
occurrence_count: 1
related_signals: []
---

## What Happened

GSD project-level hooks (`.claude/hooks/*.js`) failed at session startup with `ReferenceError: require is not defined in ES module scope`. The project's `package.json` has `"type": "module"`, which causes Node.js to treat all `.js` files as ESM — including the GSD hook scripts that use `require()` (CommonJS).

All three project-level hooks were affected:
- `gsd-check-update.js`
- `gsd-version-check.js`
- `gsd-statusline.js`

The global hooks at `~/.claude/hooks/` were unaffected because they sit outside the project directory and are not governed by the project's `package.json`.

## Context

Discovered during session startup on 2026-03-11. The SessionStart hooks failed silently (Claude Code reported hook failure but continued). This had likely been failing since the hooks were installed, as the project has always had `"type": "module"` in its `package.json`.

The fix was straightforward: rename all project-level hook files from `.js` to `.cjs` and update `.claude/settings.json` references. The `.cjs` extension forces Node.js to use CommonJS regardless of the `package.json` `type` field.

## Potential Cause

**Root cause: GSD hook templates are written as CommonJS but installed with `.js` extension.**

GSD generates hook files using `require()` syntax (CommonJS) but gives them a `.js` extension. In projects with `"type": "module"` in `package.json`, Node.js interprets `.js` as ESM, causing the `require()` calls to fail.

**Convention:** GSD hooks should use the `.cjs` extension by default, since they use CommonJS `require()` and may be installed into ESM projects. Alternatively, the hooks could be rewritten to use ESM `import` syntax, but `.cjs` is the simpler and more compatible fix.
