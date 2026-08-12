from apps.accounts.models import PaymentMethod

from .base import IPaymentProcessor
from .binance import BinanceProcessor
from .pago_movil import PagoMovilProcessor
from .paypal import PaypalProcessor
from .zelle import ZelleProcessor

_PROCESSORS: dict[str, type[IPaymentProcessor]] = {
    PaymentMethod.PAYPAL: PaypalProcessor,
    PaymentMethod.BINANCE: BinanceProcessor,
    PaymentMethod.PAGO_MOVIL: PagoMovilProcessor,
    PaymentMethod.ZELLE: ZelleProcessor,
}


class Payment:
    @staticmethod
    def create(method: str) -> IPaymentProcessor:
        try:
            processor_cls = _PROCESSORS[method]
        except KeyError:
            raise ValueError(f"[VesPay] Método de pago no soportado: {method}") from None
        return processor_cls()
