#!/bin/bash
echo "Setting up Tether environment..."

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

if [ ! -f "tether/ml/artifacts/propensity_model.joblib" ]; then
    echo "Training the LightGBM S-Learner Propensity Model..."
    python3 tether/ml/train_propensity.py
fi

echo "Starting Tether API..."
python3 -m tether.api.main
