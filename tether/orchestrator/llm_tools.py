import json
import os
from anthropic import Anthropic
from tether.domain.models import Customer, RecoveryOpportunity, Transaction

class LLMDiagnostics:
    """
    Uses an LLM (Anthropic) to diagnose the specific text/context of a failure
    and extract actionable commitments if there are customer replies.
    """
    def __init__(self):
        # We handle missing keys gracefully for the local demo.
        api_key = os.getenv("ANTHROPIC_API_KEY", "mock_key")
        self.is_mock = api_key == "mock_key"
        if not self.is_mock:
            self.client = Anthropic(api_key=api_key)

    def extract_commitment(self, text: str) -> dict:
        """Extracts date and amount from free text using Claude."""
        if self.is_mock:
            return {"has_commitment": False}
            
        prompt = f"""
        Extract any payment promise from this text: "{text}"
        Return JSON exactly matching: {{"has_commitment": bool, "promise_date": "YYYY-MM-DD" or null}}
        """
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            return json.loads(response.content[0].text)
        except:
            return {"has_commitment": False}

    def diagnose_failure(self, customer: Customer, opportunity: RecoveryOpportunity, history: list) -> str:
        """Uses LLM to evaluate the nuanced reasons for failure if there's complex metadata."""
        if self.is_mock:
            # Fallback to rules if no API key
            if customer.metadata.get("behavior_archetype") == "reliable":
                return "insufficient_funds_temporary"
            return "chronic_failure"
            
        prompt = f"""
        Diagnose the payment failure based on this profile:
        Customer: {customer.name}, LTV: {customer.lifetime_value}
        Total Successes: {customer.total_successful_payments}
        Amount at risk: {opportunity.amount_at_risk}
        
        Is this a 'temporary_hold', 'insufficient_funds_temporary', or 'chronic_failure'?
        Return ONLY the string category name.
        """
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
