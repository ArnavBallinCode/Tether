from datetime import datetime
from typing import Tuple, List
from tether.domain.models import RecoveryOpportunity, ActionType, Intervention, Customer

class PolicyGuard:
    MAX_RETRIES = 3
    HUMAN_REVIEW_THRESHOLD_USD = 10000
    
    @classmethod
    def validate_action(cls, opp: RecoveryOpportunity, customer: Customer, action: ActionType) -> Tuple[bool, str]:
        """Validates if an action is allowed based on deterministic rules."""
        
        # 1. Stop Recovery check
        if action == ActionType.STOP_RECOVERY:
            return True, "Stop recovery is always allowed."
            
        # 2. Max Retries check
        if action == ActionType.RETRY_PAYMENT:
            if opp.retry_count >= cls.MAX_RETRIES:
                return False, f"Maximum retry limit ({cls.MAX_RETRIES}) reached."
                
        # 3. Escalation check
        if action != ActionType.ESCALATE_TO_HUMAN and opp.amount_at_risk > cls.HUMAN_REVIEW_THRESHOLD_USD:
             return False, f"Opportunity exceeds human review threshold (${cls.HUMAN_REVIEW_THRESHOLD_USD}). Must escalate."
             
        # 4. Duplicate Action check (Naive)
        if opp.interventions:
            last_action = opp.interventions[-1]
            if last_action.action_type == action and action in [ActionType.REQUEST_UPDATE, ActionType.SEND_REMINDER]:
                return False, "Cannot repeat the same communication action consecutively without a cooldown."
                
        return True, "Policy check passed."
