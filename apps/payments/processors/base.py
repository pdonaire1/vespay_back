from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PaymentRequest:
    amount: Decimal
    currency: str
    sender_id: str
    recipient_id: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentResult:
    transaction_id: str
    status: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    fee: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")


class IPaymentProcessor(ABC):
    @abstractmethod
    def validate_credentials(self, account) -> bool:
        """Verifica que las credenciales vinculadas sean válidas para la pasarela."""

    @abstractmethod
    def execute(self, request: PaymentRequest) -> PaymentResult:
        """Ejecuta el débito/transferencia en la pasarela."""

    @abstractmethod
    def check_status(self, transaction_id: str) -> str:
        """Consulta el estado de una transacción en la pasarela."""
