import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Any

class PropensityModel:
    """
    S-Learner Propensity Model for estimating P(pay | features, intervention).
    """
    def __init__(self):
        model_path = Path(__file__).parent / "artifacts" / "propensity_model.joblib"
        if model_path.exists():
            self.model = joblib.load(model_path)
            self.is_trained = True
        else:
            self.model = None
            self.is_trained = False

    def _extract_features(self, customer: Any, opportunity: Any, prs_score: float, action: str) -> np.ndarray:
        # Encode action
        action_map = {
            "retry_payment": 0,
            "delay_retry": 1,
            "request_update": 2,
            "send_reminder": 3,
            "escalate_to_human": 4,
            "none": 5
        }
        action_idx = action_map.get(action, 5)
        
        return np.array([[
            customer.lifetime_value,
            customer.total_successful_payments,
            customer.account_age_days,
            opportunity.amount_at_risk,
            prs_score,
            action_idx
        ]])

    def predict_proba(self, customer: Any, opportunity: Any, prs_score: float, action: str) -> float:
        if self.is_trained and self.model is not None:
            features = self._extract_features(customer, opportunity, prs_score, action)
            # Use LightGBM to predict positive class probability
            return float(self.model.predict_proba(features)[0][1])
            
        # Fallback if no model is found
        return 0.1

class EIVCalculator:
    """
    Computes Expected Incremental Value (EIV).
    EIV = amount * [P(pay|intervention) - P(pay|no intervention)] - cost(intervention)
    """
    INTERVENTION_COSTS = {
        "retry_payment": 0.50,       # processor fee
        "delay_retry": 0.0,
        "request_update": 0.10,      # email cost
        "send_reminder": 0.10,
        "escalate_to_human": 25.0,   # 15 mins of human time
        "stop_recovery": 0.0
    }

    def __init__(self, model: PropensityModel):
        self.model = model

    def calculate_eiv(self, customer: Any, opportunity: Any, prs_score: float, action: str) -> float:
        if action == "stop_recovery":
            return 0.0
            
        amount = opportunity.amount_at_risk
        
        prob_with_action = self.model.predict_proba(customer, opportunity, prs_score, action)
        prob_none = self.model.predict_proba(customer, opportunity, prs_score, "none")
        
        cost = self.INTERVENTION_COSTS.get(action, 1.0)
        
        incremental_prob = prob_with_action - prob_none
        eiv = (amount * incremental_prob) - cost
        return eiv

