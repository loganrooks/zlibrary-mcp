#!/bin/bash
# Fix Cache Venv - Reinstall zlibrary with correct project location
#
# This script fixes issues when:
# 1. Project has been moved to a new location
# 2. Cache venv has stale editable install pointing to old location
# 3. ImportError occurs when running MCP tools
#
# The venv-manager uses a shared cache venv at ~/.cache/zlibrary-mcp/
# instead of the project-local venv. If the project moves, the editable
# zlibrary install becomes stale and needs to be updated.

set -e

echo "🔧 Z-Library MCP - Cache Venv Fix"
echo "=================================="
echo ""

# Get the project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Cache venv location
CACHE_VENV="$HOME/.cache/zlibrary-mcp/zlibrary-mcp-venv"
CACHE_PYTHON="$CACHE_VENV/bin/python"

# Check if cache venv exists
if [ ! -d "$CACHE_VENV" ]; then
    echo "❌ Cache venv not found at: $CACHE_VENV"
    echo "   Run 'npm run build' first to create the venv."
    exit 1
fi

echo "📍 Project location: $PROJECT_ROOT"
echo "📁 Cache venv: $CACHE_VENV"
echo ""

# Check current zlibrary installation
echo "🔍 Checking current zlibrary installation..."
CURRENT_ZLIB=$($CACHE_PYTHON -m pip show zlibrary 2>/dev/null | grep "Location:" | awk '{print $2}' || echo "NOT_INSTALLED")

if [ "$CURRENT_ZLIB" != "NOT_INSTALLED" ]; then
    echo "   Current zlibrary location: $CURRENT_ZLIB"
else
    echo "   ⚠️  zlibrary not installed in cache venv"
fi

echo ""
echo "🔄 Reinstalling zlibrary with current project location..."

# Reinstall zlibrary as editable from current project
$CACHE_PYTHON -m pip install -e "$PROJECT_ROOT/zlibrary" --force-reinstall --no-deps

echo ""
echo "✅ Verifying zlibrary installation..."

# Verify import works
if $CACHE_PYTHON -c "from zlibrary import Extension, Language; print('✅ zlibrary imports successful')" 2>&1; then
    echo ""
    echo "🎉 Cache venv fixed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Restart Claude Code in your other workspace"
    echo "   2. Try the Z-Library search again"
    echo "   3. Should now work without ImportError"
    exit 0
else
    echo ""
    echo "❌ Fix failed - zlibrary still not importing correctly"
    echo "   Please check the error messages above"
    exit 1
fi
