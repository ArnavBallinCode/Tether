#!/bin/bash
echo "Setting up Tether environment..."

# Detect if uv is installed
if command -v uv >/dev/null 2>&1; then
    echo "Using uv for fast installation..."
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    echo "Using standard pip..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

echo "Starting Tether API..."
python3 -m tether.api.main
