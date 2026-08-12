from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.fees import calculate_fee
from apps.payments.matchmaking import select_payment_method
from apps.payments.models import PaymentStatus, Transaction

from .models import NFCSession, NFCStatus, PayeeToken, PayerToken, TokenState
from .serializers import PayeeTokenCreateSerializer, ProcessPaymentSerializer
from .services import (
    create_payee_token,
    create_payer_token,
    notify_session,
    validate_token_signature,
)

_PAYER_PREFIX = "vsp_ptk"
_PAYEE_PREFIX = "vsp_ytk"


class PayerTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = create_payer_token(request.user)
        return Response(
            {"payer_token": token.token, "expires_at": token.expires_at},
            status=status.HTTP_201_CREATED,
        )


class PayeeTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PayeeTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = create_payee_token(request.user, **serializer.validated_data)
        return Response(
            {"payee_token": token.token, "expires_at": token.expires_at},
            status=status.HTTP_201_CREATED,
        )


class ProcessPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProcessPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payer_token_raw = serializer.validated_data["payer_token"]
        payee_token_raw = serializer.validated_data["payee_token"]

        if not validate_token_signature(payer_token_raw, _PAYER_PREFIX) or not (
            validate_token_signature(payee_token_raw, _PAYEE_PREFIX)
        ):
            return Response({"detail": "Token inválido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payer_token = PayerToken.objects.select_related("user").get(token=payer_token_raw)
            payee_token = PayeeToken.objects.select_related("user").get(token=payee_token_raw)
        except (PayerToken.DoesNotExist, PayeeToken.DoesNotExist):
            return Response(
                {"detail": "Token no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payer_token.is_expired or payee_token.is_expired:
            return Response({"detail": "Token expirado"}, status=status.HTTP_400_BAD_REQUEST)

        if payer_token.state != TokenState.PENDING or payee_token.state != TokenState.PENDING:
            return Response({"detail": "Token ya utilizado"}, status=status.HTTP_400_BAD_REQUEST)

        method = select_payment_method(payer_token.user, payee_token.user)
        if method is None:
            return Response(
                {"detail": "No hay métodos de pago compatibles entre emisor y receptor"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fee, net_amount = calculate_fee(payee_token.amount)

        transaction = Transaction.objects.create(
            sender=payer_token.user,
            recipient=payee_token.user,
            method=method,
            amount=payee_token.amount,
            currency=payee_token.currency,
            fee=fee,
            net_amount=net_amount,
            status=PaymentStatus.PROCESSING,
        )

        session = NFCSession.objects.create(
            payer_token=payer_token,
            payee_token=payee_token,
            transaction=transaction,
            status=NFCStatus.PENDING,
        )

        payer_token.state = TokenState.USED
        payee_token.state = TokenState.USED
        payer_token.save(update_fields=["state"])
        payee_token.save(update_fields=["state"])

        notify_session(
            session.id,
            "PAYMENT_PROCESSING",
            {
                "status": PaymentStatus.PROCESSING,
                "transaction_id": str(transaction.id),
                "amount": str(payee_token.amount),
                "currency": payee_token.currency,
            },
        )

        return Response(
            {
                "session_id": str(session.id),
                "transaction_id": str(transaction.id),
                "status": PaymentStatus.PROCESSING,
            },
            status=status.HTTP_202_ACCEPTED,
        )
