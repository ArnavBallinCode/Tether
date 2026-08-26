from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import logging

logger = logging.getLogger(__name__)

from tether.simulator.data_generator import seed_database
from tether.simulator.engine import SimulatedDB, SimulatedCustomerRepository, SimulatedPaymentProvider, SimulatedCommunicationProvider
from tether.orchestrator.workflow import RecoveryWorkflow
from tether.domain.models import ActionType

app = FastAPI(title="Tether API")
app.mount("/static", StaticFiles(directory="tether/ui"), name="static")

# In-memory database for demo
customers, txs, opps = seed_database()
db = SimulatedDB(customers, txs, opps)
repo = SimulatedCustomerRepository(db)
payment = SimulatedPaymentProvider(db)
comm = SimulatedCommunicationProvider(db)
workflow = RecoveryWorkflow(payment, comm, repo, db.audit_logs)

@app.get("/")
def read_index():
    return FileResponse("tether/ui/index.html")

@app.post("/api/run_recovery")
def run_recovery(background_tasks: BackgroundTasks):
    def process_all():
        logger.info("Starting batch recovery process")
        for opp in db.opportunities.values():
            if opp.status == "open":
                workflow.process_opportunity(opp)
        logger.info("Finished batch recovery process")
        
    background_tasks.add_task(process_all)
    return {"status": "started", "message": "Recovery workflow started in background"}

@app.get("/api/dashboard_metrics")
def get_metrics():
    total_risk = sum(o.amount_at_risk for o in db.opportunities.values())
    total_recovered = sum(o.recovered_amount for o in db.opportunities.values() if o.status == "recovered")
    total_opportunities = len(db.opportunities)
    
    status_counts = {"open": 0, "recovered": 0, "failed": 0, "escalated": 0}
    for o in db.opportunities.values():
        status_counts[o.status] += 1
        
    automation_rate = (status_counts["recovered"] + status_counts["failed"]) / total_opportunities if total_opportunities > 0 else 0
        
    return {
        "revenue_at_risk": total_risk,
        "money_recovered": total_recovered,
        "total_cases": total_opportunities,
        "status_breakdown": status_counts,
        "automation_rate": automation_rate
    }

@app.get("/api/opportunities")
def list_opportunities():
    # Return enriched list
    result = []
    for opp in db.opportunities.values():
        customer = db.customers[opp.customer_id]
        result.append({
            "id": opp.id,
            "customer_name": customer.name,
            "amount_at_risk": opp.amount_at_risk,
            "status": opp.status,
            "risk_level": opp.risk_level,
            "likely_cause": opp.likely_cause,
            "recovered_amount": opp.recovered_amount
        })
    return result

@app.get("/api/audit_logs")
def get_audit_logs():
    return [log.dict() for log in reversed(db.audit_logs[-100:])]

@app.post("/api/reset")
def reset_db():
    global db, repo, payment, comm, workflow
    customers, txs, opps = seed_database()
    db = SimulatedDB(customers, txs, opps)
    repo = SimulatedCustomerRepository(db)
    payment = SimulatedPaymentProvider(db)
    comm = SimulatedCommunicationProvider(db)
    workflow = RecoveryWorkflow(payment, comm, repo, db.audit_logs)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("tether.api.main:app", host="0.0.0.0", port=8000, reload=True)
