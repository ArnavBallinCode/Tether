from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ActionType(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    DELAY_RETRY = "delay_retry"
    REQUEST_UPDATE = "request_update"
    SEND_REMINDER = "send_reminder"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    STOP_RECOVERY = "stop_recovery"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    lifetime_value: float
    total_successful_payments: int
    historical_dispute_rate: float
    account_age_days: int
    is_enterprise: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    amount: float
    currency: str = "USD"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str # "success", "failed", "pending"
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None

class Intervention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    opportunity_id: str
    action_type: ActionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending" # pending, completed, failed, blocked
    confidence: float
    reasoning: str
    cost_estimate: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecoveryOpportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    failed_transaction_id: str
    amount_at_risk: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Diagnosis
    risk_level: Optional[RiskLevel] = None
    likely_cause: Optional[str] = None
    recovery_probability: Optional[float] = None
    
    # State
    status: str = "open" # open, recovered, failed, escalated
    recovered_amount: float = 0.0
    interventions: List[Intervention] = Field(default_factory=list)
    retry_count: int = 0
    next_action_allowed_after: Optional[datetime] = None

class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    opportunity_id: str
    action: str
    details: Dict[str, Any]
    passed_guardrails: bool = True
    guardrail_notes: Optional[str] = None
