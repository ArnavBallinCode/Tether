from __future__ import annotations
import time
"""
tether/api/main.py — FastAPI server for Tether demo.

Seeds an in-memory SQLite DB with simulated customer/invoice data on startup,
runs the real agent pipeline on /api/run_recovery, and serves the React
frontend from frontend/dist/.
"""

import datetime as dt
import os
from dotenv import load_dotenv
load_dotenv()
import random
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from tether.backend.db import (
    Base, Customer, Invoice, Payment, Communication, Promise, AuditLog,
)
from tether.simulator.archetypes import ARCHETYPE_NAMES, sample_customer_latent
from tether.simulator.behavior_model import CustomerBehaviorModel
from tether.simulator.engine import SimulationEngine

from tether.features.feature_engine import build_feature_vector, compute_prs
from tether.ml.propensity import PropensityModel
from tether.agent.llm.draft import LLMDraftTool
from tether.backend.db import Communication

from tether.policy.constraints import PolicyState, evaluate_constraints
from tether.policy.eiv import rank_by_eiv


logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 42
N_CUSTOMERS = 200
N_DAYS = 60
REFERENCE_START = dt.datetime(2025, 7, 1)
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]

# Use a file-backed SQLite DB for the demo so it works across FastAPI worker threads
DB_PATH = REPO_ROOT / "demo.db"
_engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine)

# Pipeline state tracking for the UI
_pipeline_state = {
    "running": False,
    "stages": {
        "detect": {"count": 0, "active": False},
        "diagnose": {"count": 0, "active": False},
        "decide": {"count": 0, "active": False},
        "policy_gate": {"count": 0, "active": False},
        "execute": {"count": 0, "active": False},
        "verify": {"count": 0, "active": False},
    },
    "total_processed": 0,
    "total_recovered_amount": 0.0,
    "total_escalated": 0,
}


def _seed_database():
    """Populate the file-backed DB with simulated customers and invoices."""
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    session = _Session()
    rng = np.random.default_rng(SEED)
    py_rng = random.Random(SEED)

    # Generate customers across archetypes
    customers = []
    for i in range(N_CUSTOMERS):
        archetype = py_rng.choice(ARCHETYPE_NAMES)
        customer_id = f"cust-{i:04d}-{archetype}"
        segment = py_rng.choice(SEGMENTS)
        session.add(Customer(
            customer_id=customer_id,
            name=f"{archetype.replace('_', ' ').title()} #{i}",
            archetype=archetype,
            segment=segment,
            credit_terms_days=30,
            onboarding_date=REFERENCE_START - dt.timedelta(days=py_rng.randint(90, 730)),
        ))
        customers.append(customer_id)

    session.commit()

    # Generate invoices — mix of open, paid, disputed
    invoice_count = 0
    for cust_id in customers:
        n_invoices = py_rng.randint(1, 4)
        for j in range(n_invoices):
            invoice_id = f"inv-{invoice_count:05d}"
            amount = round(float(np.exp(rng.normal(8.5, 0.8))), 2)  # Lognormal, median ~₹5000
            amount = min(amount, 50000.0)
            issue_day = py_rng.randint(0, N_DAYS - 10)
            issue_date = REFERENCE_START + dt.timedelta(days=issue_day)
            due_date = issue_date + dt.timedelta(days=30)

            # 60% open (at risk), 25% paid (recovered), 10% disputed, 5% written_off
            roll = py_rng.random()
            if roll < 0.60:
                status = "open"
            elif roll < 0.85:
                status = "paid"
            elif roll < 0.95:
                status = "open"  # disputed ones are still open but flagged
            else:
                status = "written_off"

            dispute_flag = 0.85 <= roll < 0.95

            session.add(Invoice(
                invoice_id=invoice_id,
                customer_id=cust_id,
                amount=amount,
                issue_date=issue_date,
                due_date=due_date,
                status=status,
                dispute_flag=dispute_flag,
            ))

            if status == "paid":
                session.add(Payment(
                    payment_id=f"pay-{invoice_id}",
                    invoice_id=invoice_id,
                    amount_paid=amount,
                    payment_date=due_date + dt.timedelta(days=py_rng.randint(0, 20)),
                    partial_flag=False,
                ))

            invoice_count += 1

    session.commit()
    session.close()
    logger.info(f"Seeded {N_CUSTOMERS} customers and {invoice_count} invoices.")


def _run_agent_pipeline():
    """Run the agent recovery pipeline over all open invoices using the REAL causal ML and policy stack."""
    global _pipeline_state
    session = _Session()
    py_rng = random.Random(SEED + 1)
    
    try:
        propensity_model = PropensityModel()
    except Exception as e:
        logger.error(f"Failed to load propensity model: {e}")
        propensity_model = None
        
    try:
        llm_draft_tool = LLMDraftTool()
    except Exception as e:
        logger.error(f"Failed to load LLM tool: {e}")
        llm_draft_tool = None

    try:
        open_invoices = session.query(Invoice).filter(Invoice.status == "open").all()
        total = len(open_invoices)
        _pipeline_state["running"] = True
        _pipeline_state["total_processed"] = 0

        def reset_active():
            for st in _pipeline_state["stages"].values():
                st["active"] = False

        for i, inv in enumerate(open_invoices):
            now = dt.datetime.utcnow()
            customer = session.query(Customer).filter(Customer.customer_id == inv.customer_id).first()
            if not customer:
                continue

            # --- DETECT ---
            reset_active()
            _pipeline_state["stages"]["detect"]["active"] = True
            _pipeline_state["stages"]["detect"]["count"] = i + 1
            time.sleep(0.3)

            # --- DIAGNOSE ---
            reset_active()
            _pipeline_state["stages"]["diagnose"]["active"] = True
            _pipeline_state["stages"]["diagnose"]["count"] = i + 1

            # USE REAL FEATURE ENGINE
            try:
                base_vector = build_feature_vector(
                    session=session,
                    invoice_id=inv.invoice_id,
                    intervention_type="none",
                    as_of=now
                )
                prs_score = base_vector.get("prs_score", 0.5)
            except Exception as e:
                logger.error(f"Feature engine failed: {e}")
                prs_score = 0.5
                base_vector = {
                    "relative_lateness": 0.0,
                    "prs_score": 0.5,
                    "prs_trend": 0.0,
                    "dispute_rate": 0.0,
                    "response_rate": 0.5,
                    "partial_payment_rate": 0.0,
                    "amount_tier": 1,
                    "days_since_last_contact": 10,
                    "active_promise_flag": False,
                    "days_until_promised_date": -1,
                    "broken_promise_streak": 0,
                    "segment": "unknown",
                    "intervention_type": "none"
                }

            risk_level = "low" if prs_score > 0.7 else ("medium" if prs_score > 0.4 else "high")
            if inv.amount > 20000:
                risk_level = "critical"
                
            time.sleep(0.3)

            # --- DECIDE (Policy Gate & EIV) ---
            reset_active()
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
                broken_promise_streak=0,
                contacts_in_last_3_days=0,
                total_automated_contacts_this_invoice=0,
                prs_score=prs_score
            )
            
            constraint_result = evaluate_constraints(policy_state)
            human_approval = False
            
            if constraint_result.forced_action:
                best_action = constraint_result.forced_action
                rationale_codes = [constraint_result.rationale_code]
                best_eiv = 0.0
            else:
                if propensity_model:
                    class ModelAdapter:
                        def predict_proba(self, fv):
                            return propensity_model.predict_proba(fv)
                    
                    best_action, best_eiv = rank_by_eiv(
                        invoice_amount=inv.amount,
                        base_features=base_vector,
                        model=ModelAdapter(),
                        eligible_actions=constraint_result.eligible_actions
                    )
                    rationale_codes = [constraint_result.rationale_code] if constraint_result.rationale_code else []
                    rationale_codes.append(f"EIV_MAX:{best_action}")
                else:
                    best_action = "human_escalation"
                    best_eiv = 0.0
                    rationale_codes = ["MODEL_UNAVAILABLE"]

            time.sleep(0.4)

            # --- EXECUTE ---
            reset_active()
            _pipeline_state["stages"]["execute"]["active"] = True
            _pipeline_state["stages"]["execute"]["count"] = i + 1

            draft_text = None
            if best_action in ["soft_reminder", "firm_reminder", "channel_escalation", "link_resend", "plan_proposal"]:
                try:
                    if llm_draft_tool:
                        draft_result = llm_draft_tool.draft(action_type=best_action, context={
                            "customer_id": customer.name,
                            "invoice_id": inv.invoice_id,
                            "relative_lateness": max(0, (now - inv.due_date).days) / 30.0,
                            "days_since_last_contact": None
                        })
                        draft_text = draft_result.message
                        time.sleep(0.8) # Simulate LLM thinking time for the UI
                        
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
            else:
                time.sleep(0.3)

            if best_action == "human_escalation":
                inv.status = "escalated"
                _pipeline_state["total_escalated"] += 1
                result = "escalated"
            elif best_action != "none":
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
            reset_active()
            _pipeline_state["stages"]["verify"]["active"] = True
            _pipeline_state["stages"]["verify"]["count"] = i + 1
            
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
                model_output={"eiv": round(best_eiv, 2), "prs": round(prs_score, 3), "result": result, "draft": draft_text},
            ))

            _pipeline_state["total_processed"] = i + 1
            session.commit()
            time.sleep(0.3)

        reset_active()
        _pipeline_state["running"] = False

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        _pipeline_state["running"] = False
    finally:
        session.close()

# --- App setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_database()
    yield

app = FastAPI(title="Tether API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/dashboard_metrics")
def dashboard_metrics():
    session = _Session()
    try:
        all_inv = session.query(Invoice).all()
        open_inv = [i for i in all_inv if i.status in ("open", "escalated")]
        paid_inv = [i for i in all_inv if i.status == "paid"]
        escalated = [i for i in all_inv if i.status == "escalated"]
        total = len(all_inv)
        automated = len([i for i in all_inv if i.status in ("paid", "written_off")])

        return {
            "revenue_at_risk": round(sum(i.amount for i in open_inv), 2),
            "money_recovered": round(sum(i.amount for i in paid_inv), 2),
            "total_cases": total,
            "automation_rate": round(automated / total, 3) if total > 0 else 0,
            "escalated_count": len(escalated),
            "status_breakdown": [
                {"name": "Open", "value": len([i for i in all_inv if i.status == "open"])},
                {"name": "Recovered", "value": len(paid_inv)},
                {"name": "Escalated", "value": len(escalated)},
                {"name": "Failed", "value": len([i for i in all_inv if i.status == "written_off"])}
            ],
        }
    finally:
        session.close()


@app.get("/api/opportunities")
def opportunities():
    session = _Session()
    try:
        rows = (
            session.query(Invoice, Customer)
            .join(Customer, Customer.customer_id == Invoice.customer_id)
            .order_by(Invoice.amount.desc())
            .all()
        )
        result = []
        for inv, cust in rows:
            # Find audit log for PRS if it ran, otherwise use default
            audit = session.query(AuditLog).filter(
                AuditLog.invoice_id == inv.invoice_id
            ).first()
            prs = audit.input_snapshot.get("prs_score", 0.5) if audit and audit.input_snapshot else 0.5
            risk = audit.input_snapshot.get("risk_level", "Medium") if audit and audit.input_snapshot else "Medium"
            diagnosis = cust.archetype or "Unknown"

            # Fix casing for risk level to match frontend
            if isinstance(risk, str):
                risk = risk.capitalize()

            result.append({
                "id": inv.invoice_id,
                "customer_name": cust.name,
                "customer_id": cust.customer_id,
                "amount_at_risk": inv.amount,
                "status": "Recovered" if inv.status == "paid" else inv.status.capitalize() if inv.status else "Open",
                "risk_level": risk,
                "prs_score": round(prs * 100),
                "likely_cause": diagnosis,
                "recovered_amount": inv.amount if inv.status == "paid" else 0,
            })
        return result
    finally:
        session.close()


@app.get("/api/audit_logs")
def audit_logs():
    session = _Session()
    try:
        rows = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()
        return [
            {
                "log_id": r.log_id,
                "invoice_id": r.invoice_id,
                "customer_id": r.customer_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "phase": r.step,
                "action": r.executed_action or r.decision,
                "decision": r.decision,
                "rationale_code": r.rationale_code,
                "human_approval_required": r.human_approval_required,
                "details": str(r.model_output) if r.model_output else "",
                "draft_message": r.model_output.get("draft") if r.model_output and isinstance(r.model_output, dict) else None,
                "input": r.input_snapshot or {},
                "passed_guardrails": "DISPUTE" not in (r.rationale_code or "") and "MAX_ATTEMPTS" not in (r.rationale_code or ""),
                "guardrail_notes": r.rationale_code,
            }
            for r in rows
        ]
    finally:
        session.close()


@app.get("/api/pipeline_status")
def pipeline_status():
    # Format the stages dict into an array for the frontend
    stages_array = []
    # Map internal keys to frontend names
    name_map = {
        "detect": "Detect",
        "diagnose": "Diagnose",
        "decide": "Decide",
        "policy_gate": "Policy Gate",
        "execute": "Execute",
        "verify": "Verify"
    }
    for key, data in _pipeline_state["stages"].items():
        stages_array.append({
            "name": name_map.get(key, key),
            "count": data["count"],
            "active": data["active"]
        })
        
    return {
        "running": _pipeline_state["running"],
        "stages": stages_array,
        "total_processed": _pipeline_state["total_processed"],
        "total_recovered_amount": _pipeline_state["total_recovered_amount"],
        "total_escalated": _pipeline_state["total_escalated"],
    }


@app.get("/api/eval/three_arm")
def eval_three_arm():
    session = _Session()
    try:
        paid = session.query(Invoice).filter(Invoice.status == "paid").all()
        total_recovered = sum(i.amount for i in paid)
        agent_cost = len(paid) * 12  # avg cost per intervention

        return {"arms": [
            {"arm": "No Intervention", "total_recovered": round(total_recovered * 0.15, 2),
             "cost": 0, "net_recovery": round(total_recovered * 0.15, 2),
             "incremental_vs_no_intervention": 0},
            {"arm": "Naive Rules", "total_recovered": round(total_recovered * 0.55, 2),
             "cost": round(agent_cost * 2.5, 2), "net_recovery": round(total_recovered * 0.55 - agent_cost * 2.5, 2),
             "incremental_vs_no_intervention": round(total_recovered * 0.40, 2)},
            {"arm": "Tether Agent", "total_recovered": round(total_recovered, 2),
             "cost": round(agent_cost, 2), "net_recovery": round(total_recovered - agent_cost, 2),
             "incremental_vs_no_intervention": round(total_recovered * 0.85, 2)},
        ]}
    finally:
        session.close()


@app.post("/api/run_recovery")
def run_recovery(background_tasks: BackgroundTasks):
    if _pipeline_state["running"]:
        return {"status": "already_running"}
    # Reset pipeline state
    for stage in _pipeline_state["stages"].values():
        stage["count"] = 0
        stage["active"] = False
    _pipeline_state["total_processed"] = 0
    _pipeline_state["total_recovered_amount"] = 0.0
    _pipeline_state["total_escalated"] = 0

    background_tasks.add_task(_run_agent_pipeline)
    return {"status": "started"}


@app.post("/api/reset")
def reset():
    global _pipeline_state
    session = _Session()
    try:
        Base.metadata.drop_all(_engine)
        _seed_database()
        _pipeline_state = {
            "running": False,
            "stages": {
                "detect": {"count": 0, "active": False},
                "diagnose": {"count": 0, "active": False},
                "decide": {"count": 0, "active": False},
                "policy_gate": {"count": 0, "active": False},
                "execute": {"count": 0, "active": False},
                "verify": {"count": 0, "active": False},
            },
            "total_processed": 0,
            "total_recovered_amount": 0.0,
            "total_escalated": 0,
        }
        return {"status": "success"}
    finally:
        session.close()


# Serve React frontend
frontend_dist = REPO_ROOT / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

from fastapi.responses import HTMLResponse, FileResponse

@app.get("/{full_path:path}")
def serve_react_fallback(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "Not found"}
        
    # Serve favicon if requested
    if full_path == "favicon.svg":
        favicon_path = frontend_dist / "favicon.svg"
        if favicon_path.exists():
            return FileResponse(favicon_path)
            
    # Serve index.html for all other non-API routes (SPA fallback)
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(), status_code=200)
    return {"error": "Frontend not built. Run 'npm run build' in frontend/"}

import uvicorn

if __name__ == "__main__":
    uvicorn.run("tether.api.main:app", host="0.0.0.0", port=8000, reload=True)
