from apps.payments.models import PaymentStatus, Transaction
from celery import shared_task

from .models import NFCSession, NFCStatus
from .services import notify_session


@shared_task
def finalize_nfc_payment(session_id: str) -> None:
    """Ejecuta el débito en la pasarela y notifica el resultado por WebSocket."""
    try:
        session = NFCSession.objects.get(id=session_id)
    except NFCSession.DoesNotExist:
        return

    transaction: Transaction = session.transaction
    if transaction is None:
        return

    # TODO: llamar a Payment.create(transaction.method).execute(...) una vez
    # implementados los procesadores concretos (PayPal, Binance, Pago Móvil, Zelle).
    transaction.status = PaymentStatus.COMPLETED
    transaction.save(update_fields=["status", "updated_at"])

    session.status = NFCStatus.COMPLETED
    session.save(update_fields=["status", "updated_at"])

    notify_session(
        session.id,
        "PAYMENT_SUCCESS",
        {
            "status": PaymentStatus.COMPLETED,
            "transaction_id": str(transaction.id),
            "amount": str(transaction.amount),
            "currency": transaction.currency,
        },
    )
