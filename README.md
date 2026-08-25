# Tether: Autonomous Revenue Recovery

Tether finds revenue that’s slipping away and wins it back.

Built for the **AI Revenue Recovery** track, Tether is an autonomous revenue operations layer that detects at-risk revenue, diagnoses the root cause, selects the optimal intervention, and executes bounded recovery workflows.

## The Problem
Revenue silently leaks across failed payments, abandoned checkouts, and overdue invoices. Most systems stop at simply flagging "This payment failed" or blindly retrying every 3 days.

## The Solution: Tether
Tether goes further:
**Detect → Diagnose → Decide → Execute → Observe → Recover**

Tether uses an AI-driven workflow bounded by deterministic guardrails to recover revenue safely and autonomously.

### Core Features
- **Realistic Recovery Simulator:** Deterministically generates synthetic customers and simulates their response to various interventions.
- **AI Case Analyzer:** Explains *why* a payment failed using historical context (e.g., "reliable customer, likely temporary lack of funds").
- **Policy Guardrails:** Deterministic rules block unauthorized actions. (e.g., stops automatic retries if amount > \$10k, escalating to humans instead).
- **Execution Engine:** Executes provider-agnostic actions (`RETRY_PAYMENT`, `SEND_REMINDER`, `ESCALATE_TO_HUMAN`).
- **Audit Trail:** Every AI decision and guardrail check is logged and visible.

## Running the Demo

This repository includes a fully functional simulation demo and a premium UI dashboard.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python -m tether.api.main
```

### 3. Open the Dashboard
Navigate to [http://localhost:8000](http://localhost:8000).

Click **"Run Recovery"** in the sidebar. You will see the agent process hundreds of at-risk cases, diagnose them, pass them through the policy guardrails, and track the **Money Recovered** in real-time on the executive dashboard.

## Architecture

- **Domain:** Provider-agnostic interfaces (`domain/interfaces.py`).
- **Orchestrator:** AI Workflow (`orchestrator/workflow.py`) and safety rules (`orchestrator/guardrails.py`).
- **Simulator:** Deterministic data engine (`simulator/engine.py`).
- **API/UI:** FastAPI + TailwindCSS frontend (`ui/`).

## Evaluation

The dashboard computes the single most important metric: **Money Recovered**. It also provides automation rates and highlights the number of cases successfully blocked from blind automation due to high value or excessive retries (escalations).

