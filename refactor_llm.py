import re
from pathlib import Path

file_path = Path("/Users/arnavangarkar/Desktop/Arnav/dev/Razorpay/promise-integrity-agent-main/tether/api/main.py")
content = file_path.read_text()

# Inject imports for LLMDraftTool and Communication model
if "from tether.agent.llm.draft import LLMDraftTool" not in content:
    import_str = "\nfrom tether.agent.llm.draft import LLMDraftTool\nfrom tether.backend.db import Communication\n"
    content = content.replace("from tether.ml.propensity import PropensityModel", "from tether.ml.propensity import PropensityModel" + import_str)

# Add LLM init in the pipeline
if "llm_draft_tool = LLMDraftTool()" not in content:
    llm_init_code = """    try:
        propensity_model = PropensityModel()
    except Exception as e:
        logger.error(f"Failed to load propensity model: {e}")
        propensity_model = None
        
    try:
        llm_draft_tool = LLMDraftTool()
    except Exception as e:
        logger.error(f"Failed to load LLM tool: {e}")
        llm_draft_tool = None"""
    content = re.sub(r'    try:\n        propensity_model = PropensityModel\(\)\n    except Exception as e:\n        logger.error\(f"Failed to load propensity model: \{e\}"\)\n        propensity_model = None', llm_init_code, content)

# Modify EXECUTE phase
execute_old = """            # --- EXECUTE ---
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
                result = "no_action" """

execute_new = """            # --- EXECUTE ---
            _pipeline_state["stages"]["execute"]["active"] = True
            _pipeline_state["stages"]["execute"]["count"] = i + 1

            # Generate real LLM Draft if action involves communication
            draft_text = None
            if best_action in ["soft_reminder", "firm_reminder", "channel_escalation", "link_resend", "plan_proposal"]:
                try:
                    draft_result = llm_draft_tool.draft(action_type=best_action, context={
                        "customer_id": customer.name,
                        "invoice_id": inv.invoice_id,
                        "relative_lateness": max(0, (now - inv.due_date).days) / 30.0,
                        "days_since_last_contact": None
                    })
                    draft_text = draft_result.message
                    
                    # Store in communications table
                    session.add(Communication(
                        comm_id=f"comm-{uuid.uuid4().hex[:8]}",
                        invoice_id=inv.invoice_id,
                        channel="email",
                        timestamp=now,
                        message_type=best_action,
                        message_text=draft_text,
                        dispatched_by="agent"
                    ))
                except Exception as e:
                    logger.error(f"LLM draft failed: {e}")
                    draft_text = f"Automated {best_action} fallback due to LLM error."

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
                result = "no_action" """

content = content.replace(execute_old, execute_new)

# Modify VERIFY phase audit log to include draft
verify_old = """                model_output={"eiv": round(best_eiv, 2), "prs": round(prs_score, 3), "result": result},"""
verify_new = """                model_output={"eiv": round(best_eiv, 2), "prs": round(prs_score, 3), "result": result, "draft": draft_text},"""
content = content.replace(verify_old, verify_new)

file_path.write_text(content)
print("LLM generation integrated successfully!")
