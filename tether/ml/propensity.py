import numpy as np
import lightgbm as lgb
from typing import Dict, Any

class PropensityModel:
    """
    S-Learner Propensity Model for estimating P(pay | features, intervention).
    """
    def __init__(self):
        # In a real production system, this would load a joblib artifact.
        # For this setup, we'll use a mocked but structurally accurate LightGBM interface.
        self.is_trained = False
        self.model = None

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
        """
        Returns estimated probability of recovery if `action` is taken.
        In demo mode, uses a heuristic function if model is not physically trained.
        """
        if self.is_trained and self.model is not None:
            features = self._extract_features(customer, opportunity, prs_score, action)
            return self.model.predict(features)[0]
            
        # Fallback to realistic mathematical heuristic based on features
        base_prob = prs_score * 0.5
        if action == "retry_payment":
            return min(0.99, base_prob + 0.1) if opportunity.retry_count < 2 else base_prob * 0.1
        elif action == "request_update":
            return min(0.99, base_prob + 0.3)
        elif action == "send_reminder":
            return min(0.99, base_prob + 0.05)
        elif action == "escalate_to_human":
            return 0.8  # Humans are effective but costly
        elif action == "none":
            return base_prob * 0.2
        return base_prob

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

