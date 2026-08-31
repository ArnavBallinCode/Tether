import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
from pathlib import Path

def generate_training_data(n_samples=20000):
    np.random.seed(42)
    # Features: lifetime_value, total_successful_payments, account_age_days, amount_at_risk, prs_score, action_idx
    
    ltv = np.random.exponential(5000, n_samples)
    successes = np.random.poisson(10, n_samples)
    age = np.random.uniform(30, 1000, n_samples)
    amount = np.random.exponential(200, n_samples)
    prs = np.random.beta(5, 2, n_samples)
    
    # 0: retry, 1: delay, 2: request_update, 3: send_reminder, 4: escalate, 5: none
    action = np.random.randint(0, 6, n_samples)
    
    # Generate realistic labels (0 or 1) based on a hidden causal function
    # base probability governed by PRS
    logits = -2.0 + (prs * 3.0) + (successes * 0.05) - (amount / 1000.0)
    
    # Add action effects (the S-learner treatment effects)
    # Retry is great if amount is small and successes are high
    retry_effect = np.where(action == 0, 1.5 - (amount/500), 0)
    # Update is good if PRS is decent
    update_effect = np.where(action == 2, prs * 1.5, 0)
    # Reminder has mild effect
    reminder_effect = np.where(action == 3, 0.5, 0)
    # Escalate has high effect
    escalate_effect = np.where(action == 4, 2.5, 0)
    
    final_logits = logits + retry_effect + update_effect + reminder_effect + escalate_effect
    probs = 1.0 / (1.0 + np.exp(-final_logits))
    
    # Add noise
    y = np.random.binomial(1, probs)
    
    X = np.column_stack([ltv, successes, age, amount, prs, action])
    return X, y

def train():
    print("Generating synthetic historical payment data...")
    X, y = generate_training_data()
    
    print("Training LightGBM Propensity Model (S-Learner)...")
    clf = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42)
    clf.fit(X, y)
    
    artifact_dir = Path(__file__).parent / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    
    model_path = artifact_dir / "propensity_model.joblib"
    joblib.dump(clf, model_path)
    print(f"Model trained and saved to {model_path}")

if __name__ == "__main__":
    train()
