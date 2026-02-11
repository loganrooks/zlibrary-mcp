#!/bin/bash
# UV-based setup script for Z-Library MCP server (v2.0.0)
#
# This script sets up the Python environment using UV (modern Python package manager)
# Replaces the old setup_venv.sh which used cache venv

set -e

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
REQUIRED="3.10"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "Error: Python $REQUIRED+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "Python $PYTHON_VERSION detected (>= $REQUIRED required)"

echo "🚀 Z-Library MCP - UV Setup (v2.0.0)"
echo "====================================="
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV not found"
    echo ""
    echo "UV is required for Python dependency management."
    echo ""
    echo "📥 Install UV:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  # Or: pip install uv"
    echo ""
    echo "Then run this script again."
    echo ""
    echo "See: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

UV_VERSION=$(uv --version)
echo "✅ UV found: $UV_VERSION"
echo ""

# Initialize UV project (creates .venv and installs deps)
echo "📦 Installing Python dependencies with UV..."
echo "   This will:"
echo "   - Create .venv/ directory"
echo "   - Install all dependencies from pyproject.toml"
echo "   - Install vendored zlibrary as editable"
echo "   - Generate uv.lock for reproducibility"
echo ""

uv sync

echo ""
echo "✅ Dependencies installed"
echo ""

# Verify zlibrary import
echo "🔍 Verifying zlibrary installation..."
if .venv/bin/python -c "from zlibrary import Extension, Language; print('✅ zlibrary ready')" 2>&1; then
    echo ""
    echo "🎉 Python environment setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. npm install         # Install Node.js dependencies"
    echo "  2. npm run build       # Build TypeScript"
    echo "  3. Configure in your MCP client"
    echo ""
    echo "💡 Tips:"
    echo "  - uv.lock file tracks exact dependencies (commit this!)"
    echo "  - .venv/ is gitignored (local to your machine)"
    echo "  - To add deps: uv add package-name"
    echo "  - To update deps: uv sync --upgrade"
else
    echo ""
    echo "❌ zlibrary import failed"
    echo "   Check the error messages above"
    exit 1
fi
