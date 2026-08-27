import math
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CustomerHistory(BaseModel):
    promises_kept: int
    promises_broken: int
    recent_latencies: List[int] # Days late for recent invoices
    lifetime_disputes: int
    total_transactions: int
    recent_responses: int # out of last 5 contacts
    recent_contacts: int

class PromiseIntegrityScore:
    """
    Computes the Promise Integrity Score (PRS) in [0, 1].
    Represents how much weight to place on a customer's stated commitments.
    """
    
    @staticmethod
    def compute(history: CustomerHistory) -> float:
        # 1. Keep Component (0.45 weight)
        total_promises = history.promises_kept + history.promises_broken
        if total_promises == 0:
            keep_comp = 0.5
        else:
            keep_comp = history.promises_kept / total_promises
            
        # 2. Trend Component (0.25 weight)
        if len(history.recent_latencies) < 2:
            trend_comp = 0.5
        else:
            # Simple slope over recent latencies. 
            # Negative slope (paying faster) -> higher score.
            diffs = [history.recent_latencies[i] - history.recent_latencies[i-1] for i in range(1, len(history.recent_latencies))]
            avg_trend = sum(diffs) / len(diffs)
            # Map trend to [0, 1]. E.g., avg_trend of -5 days (faster) maps to >0.5.
            # sigmoid mapping: 1 / (1 + exp(k * x))
            trend_comp = 1.0 / (1.0 + math.exp(0.2 * avg_trend))
            
        # 3. Dispute Component (0.15 weight)
        if history.total_transactions == 0:
            dispute_comp = 0.5
        else:
            dispute_rate = history.lifetime_disputes / history.total_transactions
            dispute_comp = 1.0 - dispute_rate
            
        # 4. Response Component (0.15 weight)
        if history.recent_contacts == 0:
            response_comp = 0.5
        else:
            response_comp = history.recent_responses / history.recent_contacts
            
        prs = (0.45 * keep_comp) + (0.25 * trend_comp) + (0.15 * dispute_comp) + (0.15 * response_comp)
        return max(0.0, min(1.0, prs))

