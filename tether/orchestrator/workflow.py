import json
import uuid
from datetime import datetime
from typing import List, Optional
from loguru import logger

from tether.domain.models import RecoveryOpportunity, ActionType, Intervention, RiskLevel, AuditLogEntry, Transaction
from tether.domain.interfaces import PaymentProvider, CommunicationProvider, CustomerRepository
from tether.orchestrator.guardrails import PolicyGuard

# Mock AI module for now (we can replace this with actual LLM calls if needed, but for hackathon demo, deterministic AI simulation is often better and faster)
class CaseAnalyzer:
    @staticmethod
    def analyze(opp: RecoveryOpportunity, customer, history) -> dict:
        reason = "temporary_hold"
        risk = RiskLevel.MEDIUM
        if opp.amount_at_risk > 10000:
            risk = RiskLevel.CRITICAL
            reason = "high_value_failure"
        elif customer.metadata.get("behavior_archetype") == "reliable":
            risk = RiskLevel.LOW
            reason = "insufficient_funds_temporary"
        elif customer.metadata.get("behavior_archetype") == "high_risk":
            risk = RiskLevel.HIGH
            reason = "chronic_failure"
            
        return {
            "risk_level": risk,
            "likely_cause": reason,
            "evidence": [f"Customer has {customer.total_successful_payments} past successful payments.",
                         f"Amount at risk is ${opp.amount_at_risk}"]
        }

class RecoveryPlanner:
    @staticmethod
    def plan(opp: RecoveryOpportunity, analysis: dict) -> dict:
        risk = analysis["risk_level"]
        reason = analysis["likely_cause"]
        
        if risk == RiskLevel.CRITICAL:
            action = ActionType.ESCALATE_TO_HUMAN
            prob = 0.0
            reasoning = "High value account requires human touch."
        elif reason == "chronic_failure":
            action = ActionType.REQUEST_UPDATE
            prob = 0.3
            reasoning = "Customer is high risk, payment retry unlikely to succeed without update."
        elif risk == RiskLevel.LOW:
            action = ActionType.RETRY_PAYMENT
            prob = 0.85
            reasoning = "Reliable customer, likely a temporary failure."
        else:
            action = ActionType.SEND_REMINDER
            prob = 0.5
            reasoning = "Standard reminder for medium risk failure."
            
        return {
            "action": action,
            "probability": prob,
            "reasoning": reasoning
        }

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
        
        # 1. Diagnose
        analysis = CaseAnalyzer.analyze(opp, customer, history)
        opp.risk_level = analysis["risk_level"]
        opp.likely_cause = analysis["likely_cause"]
        self.log_audit(opp.id, "Diagnose", analysis)
        
        # 2. Plan
        plan = RecoveryPlanner.plan(opp, analysis)
        action_type = plan["action"]
        opp.recovery_probability = plan["probability"]
        self.log_audit(opp.id, "Plan", plan)
        
        # 3. Guardrail validation
        passed, msg = PolicyGuard.validate_action(opp, customer, action_type)
        self.log_audit(opp.id, "Policy Validation", {"proposed_action": action_type}, passed, msg)
        
        if not passed:
            logger.warning(f"Guardrail blocked action {action_type} for {opp.id}: {msg}")
            # Fallback
            action_type = ActionType.STOP_RECOVERY
            plan["reasoning"] = f"Original action blocked by guardrails: {msg}"
            
        # 4. Execute
        intervention = Intervention(
            opportunity_id=opp.id,
            action_type=action_type,
            confidence=0.9,
            reasoning=plan["reasoning"]
        )
        opp.interventions.append(intervention)
        
        if action_type == ActionType.RETRY_PAYMENT:
            opp.retry_count += 1
            original_tx = next((t for t in history if t.id == opp.failed_transaction_id), None)
            new_tx = self.payment.retry_payment(opp.failed_transaction_id)
            
            if new_tx.status == "success":
                opp.status = "recovered"
                opp.recovered_amount = opp.amount_at_risk
                intervention.status = "completed"
                self.log_audit(opp.id, "Execute", {"action": "Retry Payment", "result": "Success"})
            else:
                intervention.status = "failed"
                self.log_audit(opp.id, "Execute", {"action": "Retry Payment", "result": "Failed"})
                
        elif action_type in [ActionType.REQUEST_UPDATE, ActionType.SEND_REMINDER]:
            success = self.comm.send_email(customer.id, action_type.value, {})
            intervention.status = "completed" if success else "failed"
            self.log_audit(opp.id, "Execute", {"action": action_type.value, "result": "Sent"})
            
        elif action_type == ActionType.ESCALATE_TO_HUMAN:
            opp.status = "escalated"
            intervention.status = "completed"
            self.log_audit(opp.id, "Execute", {"action": "Escalate", "result": "Sent to human queue"})
            
        elif action_type == ActionType.STOP_RECOVERY:
            opp.status = "failed"
            intervention.status = "completed"
            self.log_audit(opp.id, "Execute", {"action": "Stop Recovery", "result": "Workflow stopped"})
            
