import re
from pathlib import Path

file_path = Path("/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/tether/api/main.py")
content = file_path.read_text()

# We need to add imports:
# from tether.features.feature_engine import build_feature_vector, compute_prs
# from tether.ml.propensity import PropensityModel
# from tether.policy.constraints import PolicyState, evaluate_constraints
# from tether.policy.eiv import rank_by_eiv

import_str = """
from tether.features.feature_engine import build_feature_vector, compute_prs
from tether.ml.propensity import PropensityModel
from tether.policy.constraints import PolicyState, evaluate_constraints
from tether.policy.eiv import rank_by_eiv
"""
content = content.replace("from tether.simulator.engine import SimulationEngine", "from tether.simulator.engine import SimulationEngine\n" + import_str)

# Now, we replace the `_run_agent_pipeline` implementation.
new_pipeline_code = """def _run_agent_pipeline():
    \"\"\"Run the agent recovery pipeline over all open invoices using the REAL causal ML and policy stack.\"\"\"
    global _pipeline_state
    session = _Session()
    py_rng = random.Random(SEED + 1)
    
    try:
        propensity_model = PropensityModel()
    except Exception as e:
        logger.error(f"Failed to load propensity model: {e}")
        propensity_model = None

    try:
        open_invoices = session.query(Invoice).filter(Invoice.status == "open").all()
        total = len(open_invoices)
        _pipeline_state["running"] = True
        _pipeline_state["total_processed"] = 0

        now = dt.datetime.utcnow()

        for i, inv in enumerate(open_invoices):
            customer = session.query(Customer).filter(Customer.customer_id == inv.customer_id).first()
            if not customer:
                continue

            # --- DETECT ---
            _pipeline_state["stages"]["detect"]["count"] = i + 1
            _pipeline_state["stages"]["detect"]["active"] = True

            # --- DIAGNOSE ---
            _pipeline_state["stages"]["diagnose"]["active"] = True
            _pipeline_state["stages"]["diagnose"]["count"] = i + 1

            # USE REAL FEATURE ENGINE
            try:
                # Need a base vector without action for EIV ranking
                base_vector = build_feature_vector(
                    session=session,
                    customer_id=customer.customer_id,
                    invoice_id=inv.invoice_id,
                    action="none",
                    as_of=now
                )
                prs_score = base_vector.get("prs_score", 0.5)
            except Exception as e:
                logger.error(f"Feature engine failed: {e}")
                prs_score = 0.5
                base_vector = {"prs_score": 0.5, "amount_tier": 1}

            risk_level = "low" if prs_score > 0.7 else ("medium" if prs_score > 0.4 else "high")
            if inv.amount > 20000:
                risk_level = "critical"

            # --- DECIDE (Policy Gate & EIV) ---
            _pipeline_state["stages"]["decide"]["active"] = True
            _pipeline_state["stages"]["decide"]["count"] = i + 1
            _pipeline_state["stages"]["policy_gate"]["active"] = True
            _pipeline_state["stages"]["policy_gate"]["count"] = i + 1

            # Construct REAL PolicyState
            active_promise, days_until = False, -1
            try:
                from tether.features.feature_engine import _active_promise
                active_promise, days_until = _active_promise(session, inv.invoice_id, now)
            except:
                pass
                
            policy_state = PolicyState(
                invoice_amount=inv.amount,
                dispute_flag=inv.dispute_flag,
                no_contact_requested=False,
                active_promise_flag=active_promise,
                days_until_promised_date=days_until,
                broken_promise_streak=0,  # simplified for demo
                recent_contact_count=0,
                total_contact_count=0,
                prs_score=prs_score
            )
            
            # Evaluate constraints
            constraint_result = evaluate_constraints(policy_state)
            human_approval = False
            
            if constraint_result.forced_action:
                best_action = constraint_result.forced_action
                rationale_codes = [constraint_result.rationale_code]
                best_eiv = 0.0
            else:
                # Rank eligible actions via REAL EIV & LightGBM S-Learner
                if propensity_model:
                    class ModelAdapter:
                        def predict_proba(self, fv):
                            return propensity_model.predict_proba(fv)
                    
                    ranked = rank_by_eiv(
                        amount=inv.amount,
                        base_feature_vector=base_vector,
                        model=ModelAdapter(),
                        eligible_actions=constraint_result.eligible_actions
                    )
                    best_action = ranked[0][0]
                    best_eiv = ranked[0][1]
                    rationale_codes = [constraint_result.rationale_code] if constraint_result.rationale_code else []
                    rationale_codes.append(f"EIV_MAX:{best_action}")
                else:
                    best_action = "human_escalation"
                    best_eiv = 0.0
                    rationale_codes = ["MODEL_UNAVAILABLE"]

            # --- EXECUTE ---
            _pipeline_state["stages"]["execute"]["active"] = True
            _pipeline_state["stages"]["execute"]["count"] = i + 1

            # Simulate outcome based on action + archetype
            if best_action == "human_escalation":
                inv.status = "escalated"
                _pipeline_state["total_escalated"] += 1
                result = "escalated"
            elif best_action != "none":
                # Probability of recovery based on action quality
                recovery_prob = prs_score * 0.5 + 0.1
                if best_action == "plan_proposal":
                    recovery_prob += 0.2
                if py_rng.random() < recovery_prob:
                    inv.status = "paid"
                    session.add(Payment(
                        payment_id=f"pay-recovery-{inv.invoice_id}",
                        invoice_id=inv.invoice_id,
                        amount_paid=inv.amount,
                        payment_date=now,
                    ))
                    _pipeline_state["total_recovered_amount"] += inv.amount
                    result = "recovered"
                else:
                    result = "pending"
            else:
                result = "no_action"

            # --- VERIFY ---
            _pipeline_state["stages"]["verify"]["active"] = True
            _pipeline_state["stages"]["verify"]["count"] = i + 1

            # Write REAL audit log
            session.add(AuditLog(
                log_id=f"audit-{inv.invoice_id}-{uuid.uuid4().hex[:8]}",
                timestamp=now,
                invoice_id=inv.invoice_id,
                customer_id=inv.customer_id,
                step="full_cycle",
                input_snapshot={
                    "amount": inv.amount, "prs_score": round(prs_score, 3),
                    "risk_level": risk_level, "days_overdue": max(0, (now - inv.due_date).days),
                    "archetype": customer.archetype,
                    "features": base_vector,
                },
                decision=best_action,
                rationale_code=",".join(rationale_codes),
                executed_action=best_action,
                human_approval_required=("APPROVAL" in ",".join(rationale_codes)),
                model_output={"eiv": round(best_eiv, 2), "prs": round(prs_score, 3), "result": result},
            ))

            _pipeline_state["total_processed"] = i + 1
            session.commit()

        # Reset active flags
        for stage in _pipeline_state["stages"].values():
            stage["active"] = False
        _pipeline_state["running"] = False

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        _pipeline_state["running"] = False
    finally:
        session.close()"""

import re
content = re.sub(r'def _run_agent_pipeline\(\):.*?(?=\n\n# --- App setup ---)', new_pipeline_code, content, flags=re.DOTALL)

file_path.write_text(content)
print("Updated successfully")
