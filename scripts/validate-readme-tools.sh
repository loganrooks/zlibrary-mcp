#!/usr/bin/env bash
set -euo pipefail

# validate-readme-tools.sh
# Compares tool names registered in src/index.ts against those documented in README.md.
# Exits 0 if the sets match, exits 1 with a diff if they diverge.

# Extract tool names from server.tool() calls in src/index.ts.
# server.tool( appears on one line; the tool name string appears on the next line.
SOURCE_TOOLS=$(grep -A 1 "server\.tool(" src/index.ts | grep -oP "(?<=['\"])[a-z_]+(?=['\"])" | sort)

# Extract tool names from the README.md Available MCP Tools section only.
# Scopes to the section between "## Available MCP Tools" and the next "## " heading.
README_TOOLS=$(sed -n '/## Available MCP Tools/,/^## /p' README.md | grep -oP '(?<=\| \`)[a-z_]+(?=\`)' | sort)

SOURCE_COUNT=$(echo "$SOURCE_TOOLS" | grep -c .)
README_COUNT=$(echo "$README_TOOLS" | grep -c .)

echo "Source tools ($SOURCE_COUNT):"
echo "$SOURCE_TOOLS" | sed 's/^/  /'
echo ""
echo "README tools ($README_COUNT):"
echo "$README_TOOLS" | sed 's/^/  /'
echo ""

if [ "$SOURCE_TOOLS" = "$README_TOOLS" ]; then
  echo "OK: All $SOURCE_COUNT tools documented in README."
  exit 0
else
  echo "ERROR: Tool lists diverge between src/index.ts and README.md."
  echo ""
  echo "Diff (< source-only, > readme-only):"
  diff <(echo "$SOURCE_TOOLS") <(echo "$README_TOOLS") || true
  exit 1
fi
