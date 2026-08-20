import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from tether.domain.models import Customer, Transaction, RecoveryOpportunity

fake = Faker()
Faker.seed(42)
random.seed(42)

def generate_customers(num_customers: int) -> list[Customer]:
    customers = []
    for _ in range(num_customers):
        # 20% enterprise
        is_enterprise = random.random() < 0.2
        lifetime_value = round(random.uniform(5000, 50000) if is_enterprise else random.uniform(100, 2000), 2)
        total_successful_payments = random.randint(1, 50)
        
        customers.append(Customer(
            id=str(uuid.uuid4()),
            name=fake.company() if is_enterprise else fake.name(),
            email=fake.email(),
            lifetime_value=lifetime_value,
            total_successful_payments=total_successful_payments,
            historical_dispute_rate=random.choices([0.0, 0.05, 0.1], weights=[0.8, 0.15, 0.05])[0],
            account_age_days=random.randint(30, 1000),
            is_enterprise=is_enterprise,
            metadata={
                "industry": fake.job() if is_enterprise else None,
                "behavior_archetype": random.choice(["reliable", "forgetful", "high_risk", "churn_risk"])
            }
        ))
    return customers

def generate_failed_transactions(customers: list[Customer], num_failures: int) -> list[Transaction]:
    failures = []
    selected_customers = random.choices(customers, k=num_failures)
    
    failure_reasons = [
        ("insufficient_funds", "soft_decline"),
        ("card_expired", "hard_decline"),
        ("do_not_honor", "hard_decline"),
        ("temporary_hold", "soft_decline")
    ]
    
    for customer in selected_customers:
        amount = round(random.uniform(500, 5000) if customer.is_enterprise else random.uniform(20, 300), 2)
        reason, code = random.choices(failure_reasons, weights=[0.4, 0.3, 0.2, 0.1])[0]
        
        failures.append(Transaction(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            amount=amount,
            status="failed",
            failure_code=code,
            failure_reason=reason,
            timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 1440))
        ))
    return failures

def seed_database():
    customers = generate_customers(500)
    failed_txs = generate_failed_transactions(customers, 150)
    
    opportunities = []
    for tx in failed_txs:
        opportunities.append(RecoveryOpportunity(
            id=str(uuid.uuid4()),
            customer_id=tx.customer_id,
            failed_transaction_id=tx.id,
            amount_at_risk=tx.amount
        ))
        
    return customers, failed_txs, opportunities

if __name__ == "__main__":
    customers, txs, opps = seed_database()
    print(f"Generated {len(customers)} customers, {len(txs)} failed txs, {len(opps)} opportunities.")
