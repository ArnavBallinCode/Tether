#!/bin/bash
set -e
echo "🔌 Tether - AI Revenue Recovery Platform"
echo "========================================="

# Install Python dependencies
if command -v uv >/dev/null 2>&1; then
    echo "📦 Installing dependencies with uv..."
    uv venv 2>/dev/null || true
    source .venv/bin/activate 2>/dev/null || true
    uv pip install -r requirements.txt
else
    echo "📦 Installing dependencies with pip..."
    python3 -m venv .venv 2>/dev/null || true
    source .venv/bin/activate 2>/dev/null || true
    pip install -r requirements.txt
fi

# Build React frontend if needed
if [ ! -d "frontend/dist" ]; then
    echo "🎨 Building React frontend..."
    cd frontend && npm install && npm run build && cd ..
fi

# Train ML model if needed
if [ ! -f "tether/ml/artifacts/propensity_model.joblib" ]; then
    echo "🧠 Training LightGBM S-Learner Propensity Model..."
    python3 tether/ml/train_propensity.py
fi

echo ""
echo "🚀 Starting Tether server on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
python3 -m tether.api.main
