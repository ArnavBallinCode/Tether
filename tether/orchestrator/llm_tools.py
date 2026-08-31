import json
import os
import requests
from tether.domain.models import Customer, RecoveryOpportunity

class LLMDiagnostics:
    """
    Uses Groq (via provided API key) to diagnose the specific text/context of a failure
    and extract actionable commitments if there are customer replies.
    """
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def _call_groq(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.0
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=5)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            pass
        return ""

    def diagnose_failure(self, customer: Customer, opportunity: RecoveryOpportunity, history: list) -> str:
        """Uses LLM to evaluate the nuanced reasons for failure."""
        prompt = f"""
        Diagnose the payment failure based on this profile:
        Customer: {customer.name}, LTV: {customer.lifetime_value}
        Total Successes: {customer.total_successful_payments}
        Amount at risk: {opportunity.amount_at_risk}
        
        Is this a 'temporary_hold', 'insufficient_funds_temporary', or 'chronic_failure'?
        Return ONLY the string category name. No other text.
        """
        response_text = self.call_groq(prompt)
        
        # Clean up response in case model is chatty
        lower_resp = response_text.lower()
        if 'temporary_hold' in lower_resp: return 'temporary_hold'
        if 'insufficient_funds_temporary' in lower_resp: return 'insufficient_funds_temporary'
        if 'chronic_failure' in lower_resp: return 'chronic_failure'
        
        return "insufficient_funds_temporary" # Fallback
        
    def call_groq(self, prompt: str) -> str:
        return self._call_groq(prompt)
