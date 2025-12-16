#!/bin/bash
# Ruff linting and formatting script

echo "Running ruff checks..."
uv run ruff check src/

if [ $? -eq 0 ]; then
    echo "✓ All checks passed!"
    echo ""
    echo "Running ruff format..."
    uv run ruff format src/
    echo "✓ Formatting complete!"
else
    echo "✗ Ruff checks failed. Fix the issues and try again."
    exit 1
fi
