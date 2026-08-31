from tether.domain.models import Customer, RecoveryOpportunity
from tether.ml.propensity import PropensityModel, EIVCalculator

cust = Customer(name="test", email="test", lifetime_value=1000, total_successful_payments=10, historical_dispute_rate=0, account_age_days=100)
opp = RecoveryOpportunity(customer_id=cust.id, failed_transaction_id="mock", amount_at_risk=200)

model = PropensityModel()
calc = EIVCalculator(model)

prs = 0.8
for act in ["retry_payment", "request_update", "send_reminder", "escalate_to_human"]:
    eiv = calc.calculate_eiv(cust, opp, prs, act)
    prob = model.predict_proba(cust, opp, prs, act)
    print(f"{act} -> prob: {prob}, EIV: {eiv}")
