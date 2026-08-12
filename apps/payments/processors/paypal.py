from .base import IPaymentProcessor, PaymentRequest, PaymentResult


class PaypalProcessor(IPaymentProcessor):
    def validate_credentials(self, account) -> bool:
        raise NotImplementedError

    def execute(self, request: PaymentRequest) -> PaymentResult:
        raise NotImplementedError

    def check_status(self, transaction_id: str) -> str:
        raise NotImplementedError
