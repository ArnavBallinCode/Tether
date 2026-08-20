from typing import List, Optional, Dict
import random
import uuid
from datetime import datetime

from tether.domain.interfaces import PaymentProvider, CommunicationProvider, CustomerRepository
from tether.domain.models import Customer, Transaction, RecoveryOpportunity

class SimulatedDB:
    def __init__(self, customers: List[Customer], transactions: List[Transaction], opportunities: List[RecoveryOpportunity]):
        self.customers = {c.id: c for c in customers}
        self.transactions = {t.id: t for t in transactions}
        self.opportunities = {o.id: o for o in opportunities}
        self.audit_logs = []
        random.seed(42)

class SimulatedCustomerRepository(CustomerRepository):
    def __init__(self, db: SimulatedDB):
        self.db = db
        
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self.db.customers.get(customer_id)
        
    def get_customer_history(self, customer_id: str) -> List[Transaction]:
        return [t for t in self.db.transactions.values() if t.customer_id == customer_id]

class SimulatedPaymentProvider(PaymentProvider):
    def __init__(self, db: SimulatedDB):
        self.db = db
        
    def retry_payment(self, transaction_id: str) -> Transaction:
        original = self.db.transactions.get(transaction_id)
        if not original:
            raise ValueError("Transaction not found")
            
        customer = self.db.customers.get(original.customer_id)
        archetype = customer.metadata.get("behavior_archetype")
        
        # Deterministic simulation based on archetype and reason
        success_prob = 0.1
        if original.failure_reason == "insufficient_funds":
            success_prob = 0.8 if archetype == "reliable" else 0.4
        elif original.failure_reason == "card_expired":
            success_prob = 0.05 # Rarely works without update
        elif original.failure_reason == "temporary_hold":
            success_prob = 0.9
            
        is_success = random.random() < success_prob
        
        new_tx = Transaction(
            id=str(uuid.uuid4()),
            customer_id=original.customer_id,
            amount=original.amount,
            status="success" if is_success else "failed",
            failure_code=None if is_success else original.failure_code,
            failure_reason=None if is_success else original.failure_reason,
            timestamp=datetime.utcnow()
        )
        self.db.transactions[new_tx.id] = new_tx
        return new_tx

class SimulatedCommunicationProvider(CommunicationProvider):
    def __init__(self, db: SimulatedDB):
        self.db = db
        
    def send_email(self, customer_id: str, template: str, context: dict) -> bool:
        # Simulate always successfully sending
        return True
