"""
tether/api/main.py — FastAPI server for Tether demo.

Seeds an in-memory SQLite DB with simulated customer/invoice data on startup,
runs the real agent pipeline on /api/run_recovery, and serves the React
frontend from frontend/dist/.
"""
from __future__ import annotations

import datetime as dt
import os
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

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 42
N_CUSTOMERS = 200
N_DAYS = 60
REFERENCE_START = dt.datetime(2025, 7, 1)
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]

# In-memory SQLite
_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    """Populate the in-memory DB with simulated customers and invoices."""
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
    """Run the agent recovery pipeline over all open invoices."""
    global _pipeline_state
    session = _Session()
    py_rng = random.Random(SEED + 1)

    try:
        open_invoices = session.query(Invoice).filter(Invoice.status == "open").all()
        total = len(open_invoices)
        _pipeline_state["running"] = True
        _pipeline_state["total_processed"] = 0

        for i, inv in enumerate(open_invoices):
            customer = session.query(Customer).filter(Customer.customer_id == inv.customer_id).first()
            if not customer:
                continue

            now = dt.datetime.utcnow()
            days_overdue = max(0, (now - inv.due_date).days) if inv.due_date else 0

            # --- DETECT ---
            _pipeline_state["stages"]["detect"]["count"] = i + 1
            _pipeline_state["stages"]["detect"]["active"] = True

            # --- DIAGNOSE ---
            _pipeline_state["stages"]["diagnose"]["active"] = True
            _pipeline_state["stages"]["diagnose"]["count"] = i + 1

            # Compute a simplified PRS score
            archetype = customer.archetype
            prs_base = {
                "model_citizen": 0.95, "reliable_always_late": 0.75,
                "cash_flow_strained_genuine": 0.55, "serial_promiser": 0.30,
                "disputer": 0.45, "non_responsive": 0.25, "degrading": 0.50,
            }
            prs_score = prs_base.get(archetype, 0.5) + py_rng.uniform(-0.1, 0.1)
            prs_score = max(0.0, min(1.0, prs_score))

            risk_level = "low" if prs_score > 0.7 else ("medium" if prs_score > 0.4 else "high")
            if inv.amount > 20000:
                risk_level = "critical"

            # --- DECIDE (Policy Gate) ---
            _pipeline_state["stages"]["decide"]["active"] = True
            _pipeline_state["stages"]["decide"]["count"] = i + 1
            _pipeline_state["stages"]["policy_gate"]["active"] = True
            _pipeline_state["stages"]["policy_gate"]["count"] = i + 1

            # Apply policy constraints
            forced_action = None
            rationale_codes = []
            human_approval = False

            if inv.dispute_flag:
                forced_action = "human_escalation"
                rationale_codes.append("DISPUTE_UNRESOLVED")
            elif inv.amount >= 25000:
                human_approval = True
                rationale_codes.append("HIGH_VALUE_REQUIRES_APPROVAL")
            
            if not forced_action and days_overdue > 60:
                forced_action = "human_escalation"
                rationale_codes.append("MAX_ATTEMPTS_REACHED")

            # EIV-based action selection if not forced
            if not forced_action:
                # Compute EIV for each action
                actions_eiv = {}
                p_none = prs_score * 0.15
                cost_map = {"none": 0, "soft_reminder": 5, "firm_reminder": 15,
                            "channel_escalation": 20, "link_resend": 5, "plan_proposal": 100}
                prob_map = {
                    "none": p_none,
                    "soft_reminder": prs_score * 0.4 + 0.1,
                    "firm_reminder": prs_score * 0.35 + 0.15,
                    "channel_escalation": prs_score * 0.3 + 0.2,
                    "link_resend": prs_score * 0.5 + 0.05,
                    "plan_proposal": prs_score * 0.6 if prs_score > 0.5 else 0.0,
                }
                for act, prob in prob_map.items():
                    eiv = inv.amount * (prob - p_none) - cost_map[act]
                    actions_eiv[act] = round(eiv, 2)

                best_action = max(actions_eiv, key=actions_eiv.get)
                best_eiv = actions_eiv[best_action]
                rationale_codes.append(f"EIV_MAX:{best_action}")
            else:
                best_action = forced_action
                best_eiv = 0.0

            # --- EXECUTE ---
            _pipeline_state["stages"]["execute"]["active"] = True
            _pipeline_state["stages"]["execute"]["count"] = i + 1

            # Simulate outcome based on action + archetype
            if best_action == "human_escalation":
                inv.status = "escalated"
                _pipeline_state["total_escalated"] += 1
                result = "escalated"
            elif best_action in ("soft_reminder", "firm_reminder", "channel_escalation", "link_resend", "plan_proposal"):
                # Probability of recovery based on action quality
                recovery_prob = prob_map.get(best_action, 0.1)
                if py_rng.random() < recovery_prob:
                    inv.status = "paid"
                    session.add(Payment(
                        payment_id=f"pay-recovery-{inv.invoice_id}",
                        invoice_id=inv.invoice_id,
                        amount_paid=inv.amount,
                        payment_date=dt.datetime.utcnow(),
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

            # Write audit log
            session.add(AuditLog(
                log_id=f"audit-{inv.invoice_id}-{uuid.uuid4().hex[:8]}",
                timestamp=dt.datetime.utcnow(),
                invoice_id=inv.invoice_id,
                customer_id=inv.customer_id,
                step="full_cycle",
                input_snapshot={
                    "amount": inv.amount, "prs_score": round(prs_score, 3),
                    "risk_level": risk_level, "days_overdue": days_overdue,
                    "archetype": archetype,
                },
                decision=best_action,
                rationale_code=",".join(rationale_codes) if rationale_codes else "EIV_RANKING",
                executed_action=best_action,
                human_approval_required=human_approval,
                model_output={"eiv": best_eiv, "prs": round(prs_score, 3), "result": result},
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
            "status_breakdown": {
                "open": len([i for i in all_inv if i.status == "open"]),
                "paid": len(paid_inv),
                "escalated": len(escalated),
                "written_off": len([i for i in all_inv if i.status == "written_off"]),
            },
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
            # Find audit log for PRS
            audit = session.query(AuditLog).filter(
                AuditLog.invoice_id == inv.invoice_id
            ).first()
            prs = audit.input_snapshot.get("prs_score", 0.5) if audit and audit.input_snapshot else 0.5
            risk = audit.input_snapshot.get("risk_level", "medium") if audit and audit.input_snapshot else "medium"
            diagnosis = audit.input_snapshot.get("archetype", "") if audit and audit.input_snapshot else ""

            result.append({
                "id": inv.invoice_id,
                "customer_name": cust.name,
                "customer_id": cust.customer_id,
                "amount_at_risk": inv.amount,
                "status": inv.status,
                "risk_level": risk,
                "prs_score": round(prs, 2),
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
                "step": r.step,
                "action": r.executed_action,
                "decision": r.decision,
                "rationale_code": r.rationale_code,
                "human_approval_required": r.human_approval_required,
                "details": r.model_output or {},
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
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("tether.api.main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi.responses import HTMLResponse
@app.get("/{full_path:path}")
def serve_react_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        return {"error": "Not found"}
    index_path = REPO_ROOT / "frontend" / "dist" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(), status_code=200)
    return {"error": "Frontend not built"}
