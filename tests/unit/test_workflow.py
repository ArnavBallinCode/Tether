import pytest
from tether.domain.models import RecoveryOpportunity, Customer, Transaction, ActionType
from tether.orchestrator.workflow import RecoveryWorkflow
from tether.orchestrator.guardrails import PolicyGuard
from tether.simulator.engine import SimulatedDB, SimulatedCustomerRepository, SimulatedPaymentProvider, SimulatedCommunicationProvider

def test_guardrail_blocks_human_threshold():
    customer = Customer(name="Test", email="test@test.com", lifetime_value=50000, total_successful_payments=10, historical_dispute_rate=0.0, account_age_days=100)
    opp = RecoveryOpportunity(customer_id=customer.id, failed_transaction_id="tx_123", amount_at_risk=15000.0)
    
    # Try to retry payment for an amount over threshold
    passed, msg = PolicyGuard.validate_action(opp, customer, ActionType.RETRY_PAYMENT)
    assert not passed
    assert "exceeds human review threshold" in msg

def test_guardrail_blocks_max_retries():
    customer = Customer(name="Test", email="test@test.com", lifetime_value=500, total_successful_payments=10, historical_dispute_rate=0.0, account_age_days=100)
    opp = RecoveryOpportunity(customer_id=customer.id, failed_transaction_id="tx_123", amount_at_risk=150.0, retry_count=3)
    
    passed, msg = PolicyGuard.validate_action(opp, customer, ActionType.RETRY_PAYMENT)
    assert not passed
    assert "Maximum retry limit" in msg

def test_workflow_execution():
    customer = Customer(name="Test", email="test@test.com", lifetime_value=50000, total_successful_payments=10, historical_dispute_rate=0.0, account_age_days=100)
    tx = Transaction(customer_id=customer.id, amount=150.0, status="failed", failure_code="soft_decline", failure_reason="insufficient_funds")
    opp = RecoveryOpportunity(customer_id=customer.id, failed_transaction_id=tx.id, amount_at_risk=150.0)
    
    db = SimulatedDB([customer], [tx], [opp])
    repo = SimulatedCustomerRepository(db)
    payment = SimulatedPaymentProvider(db)
    comm = SimulatedCommunicationProvider(db)
    workflow = RecoveryWorkflow(payment, comm, repo, db.audit_logs)
    
    workflow.process_opportunity(opp)
    
    assert len(db.audit_logs) > 0
    # Check that interventions were added
    assert len(opp.interventions) == 1

