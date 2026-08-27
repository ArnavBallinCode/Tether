import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

from tether.domain.models import RecoveryOpportunity, ActionType, Intervention, RiskLevel, AuditLogEntry, Transaction
from tether.domain.interfaces import PaymentProvider, CommunicationProvider, CustomerRepository
from tether.orchestrator.guardrails import PolicyGuard
from tether.features.prs import PromiseIntegrityScore, CustomerHistory
from tether.ml.propensity import PropensityModel, EIVCalculator
from tether.orchestrator.llm_tools import LLMDiagnostics

class RecoveryWorkflow:
    def __init__(self, 
                 payment_provider: PaymentProvider, 
                 comm_provider: CommunicationProvider,
                 customer_repo: CustomerRepository,
                 db_logs: List[AuditLogEntry] = None):
        self.payment = payment_provider
        self.comm = comm_provider
        self.repo = customer_repo
        self.audit_logs = db_logs if db_logs is not None else []
        
        self.llm = LLMDiagnostics()
        self.propensity_model = PropensityModel()
        self.eiv_calc = EIVCalculator(self.propensity_model)
        
    def log_audit(self, opp_id: str, action: str, details: dict, passed: bool = True, notes: str = None):
        self.audit_logs.append(AuditLogEntry(
            opportunity_id=opp_id,
            action=action,
            details=details,
            passed_guardrails=passed,
            guardrail_notes=notes
        ))

    def process_opportunity(self, opp: RecoveryOpportunity) -> None:
        if opp.status != "open":
            return
            
        customer = self.repo.get_customer(opp.customer_id)
        history = self.repo.get_customer_history(opp.customer_id)
        
        # 1. Feature Engineering: Compute PRS Score
        # (In production, this would read from the data warehouse. Here we build history on the fly).
        cust_history = CustomerHistory(
            promises_kept=customer.metadata.get("promises_kept", 5),
            promises_broken=customer.metadata.get("promises_broken", 1),
            recent_latencies=[2, 1, 0],
            lifetime_disputes=int(customer.total_successful_payments * customer.historical_dispute_rate),
            total_transactions=customer.total_successful_payments + 1,
            recent_responses=3,
            recent_contacts=5
        )
        prs_score = PromiseIntegrityScore.compute(cust_history)
        
        # 2. AI Diagnosis
        likely_cause = self.llm.diagnose_failure(customer, opp, history)
        
        risk = RiskLevel.MEDIUM
        if opp.amount_at_risk > 10000:
            risk = RiskLevel.CRITICAL
        elif prs_score > 0.8:
            risk = RiskLevel.LOW
        elif prs_score < 0.4:
            risk = RiskLevel.HIGH
            
        opp.risk_level = risk
        opp.likely_cause = likely_cause
        self.log_audit(opp.id, "Diagnose", {"risk_level": risk.value, "likely_cause": likely_cause, "prs_score": round(prs_score, 2)})
        
        # 3. Decision via EIV Ranking
        # Generate all possible actions
        possible_actions = [a for a in ActionType]
        action_eivs = {}
        
        for action in possible_actions:
            # Check guardrails first
            passed, msg = PolicyGuard.validate_action(opp, customer, action)
            if passed:
                eiv = self.eiv_calc.calculate_eiv(customer, opp, prs_score, action.value)
                action_eivs[action] = eiv
            else:
                action_eivs[action] = -9999.0 # Effectively disqualified
                
        # Select action with maximum EIV
        best_action = max(action_eivs.items(), key=lambda x: x[1])[0]
        max_eiv = action_eivs[best_action]
        best_prob = self.propensity_model.predict_proba(customer, opp, prs_score, best_action.value)
        
        plan_details = {
            "action": best_action.value, 
            "expected_incremental_value": round(max_eiv, 2),
            "probability": round(best_prob, 2),
            "prs_score": round(prs_score, 2)
        }
        
        self.log_audit(opp.id, "Plan (EIV)", plan_details)
        
        if max_eiv <= 0 and best_action != ActionType.ESCALATE_TO_HUMAN:
            # If nothing has positive expected value, escalate or stop
            best_action = ActionType.ESCALATE_TO_HUMAN if opp.amount_at_risk > 1000 else ActionType.STOP_RECOVERY
            self.log_audit(opp.id, "Policy Validation", {"proposed_action": best_action.value}, True, "EIV < 0, fallback action")
        else:
            self.log_audit(opp.id, "Policy Validation", {"proposed_action": best_action.value}, True, "Action permitted by guardrails and EIV ranking")

        opp.recovery_probability = best_prob
        
        # 4. Execute
        intervention = Intervention(
            opportunity_id=opp.id,
            action_type=best_action,
            confidence=best_prob,
            reasoning=f"Max EIV strategy (EIV: ${round(max_eiv, 2)}, PRS: {round(prs_score, 2)})"
        )
        opp.interventions.append(intervention)
        
        if best_action == ActionType.RETRY_PAYMENT:
            opp.retry_count += 1
            new_tx = self.payment.retry_payment(opp.failed_transaction_id)
            
            if new_tx.status == "success":
                opp.status = "recovered"
                opp.recovered_amount = opp.amount_at_risk
                intervention.status = "completed"
                self.log_audit(opp.id, "Execute", {"action": "Retry Payment", "result": "Success"})
            else:
                intervention.status = "failed"
                self.log_audit(opp.id, "Execute", {"action": "Retry Payment", "result": "Failed"})
                
        elif best_action in [ActionType.REQUEST_UPDATE, ActionType.SEND_REMINDER]:
            success = self.comm.send_email(customer.id, best_action.value, {})
            intervention.status = "completed" if success else "failed"
            self.log_audit(opp.id, "Execute", {"action": best_action.value, "result": "Sent"})
            
        elif best_action == ActionType.ESCALATE_TO_HUMAN:
            opp.status = "escalated"
            intervention.status = "completed"
            self.log_audit(opp.id, "Execute", {"action": "Escalate", "result": "Sent to human queue"})
            
        elif best_action == ActionType.STOP_RECOVERY:
            opp.status = "failed"
            intervention.status = "completed"
            self.log_audit(opp.id, "Execute", {"action": "Stop Recovery", "result": "Workflow stopped"})
