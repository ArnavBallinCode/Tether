from abc import ABC, abstractmethod
from typing import List, Optional
from tether.domain.models import Customer, Transaction, RecoveryOpportunity

class PaymentProvider(ABC):
    @abstractmethod
    def retry_payment(self, transaction_id: str) -> Transaction:
        """Attempts to retry a failed payment. Returns the new transaction attempt."""
        pass
        
class CommunicationProvider(ABC):
    @abstractmethod
    def send_email(self, customer_id: str, template: str, context: dict) -> bool:
        """Sends an email communication to the customer."""
        pass
        
class CustomerRepository(ABC):
    @abstractmethod
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        pass
        
    @abstractmethod
    def get_customer_history(self, customer_id: str) -> List[Transaction]:
        pass
