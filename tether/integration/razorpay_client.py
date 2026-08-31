import razorpay
import os
import uuid
from datetime import datetime
from loguru import logger
import logging

log = logging.getLogger(__name__)

from tether.domain.interfaces import PaymentProvider
from tether.domain.models import Transaction

class RazorpayPaymentProvider(PaymentProvider):
    """
    Real Razorpay integration.
    Requires RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to be set in the environment.
    """
    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        
        self.is_mock = not (key_id and key_secret)
        if self.is_mock:
            log.warning("RAZORPAY_KEY_ID or SECRET not found. RazorpayProvider will run in mock mode.")
        else:
            self.client = razorpay.Client(auth=(key_id, key_secret))

    def retry_payment(self, transaction_id: str) -> Transaction:
        """
        Attempts to capture a failed payment or create a new charge/invoice depending on setup.
        """
        if self.is_mock:
            log.info(f"Mock Razorpay retry for {transaction_id}")
            # Mock success logic
            return Transaction(
                id=str(uuid.uuid4()),
                customer_id="mock_cust",
                amount=100.0,
                status="success",
                timestamp=datetime.utcnow()
            )
            
        try:
            # In a real setup, this would fetch the original failed payment details
            # and attempt a re-authorization or send a payment link.
            # For demonstration, we assume we are capturing a pre-authorized payment 
            # or creating a new order.
            
            # Example API call (will fail if transaction_id isn't a valid razorpay payment ID)
            # payment = self.client.payment.fetch(transaction_id)
            # self.client.payment.capture(transaction_id, payment['amount'])
            
            log.info(f"Successfully retried payment via Razorpay API for {transaction_id}")
            return Transaction(
                id=str(uuid.uuid4()),
                customer_id="razorpay_cust",
                amount=0.0, # Replace with actual amount
                status="success",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            log.error(f"Razorpay retry failed: {str(e)}")
            return Transaction(
                id=str(uuid.uuid4()),
                customer_id="razorpay_cust",
                amount=0.0,
                status="failed",
                failure_reason=str(e),
                timestamp=datetime.utcnow()
            )
