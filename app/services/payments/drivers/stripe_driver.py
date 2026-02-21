"""
Sistema ISP - Driver: Stripe
API de Stripe para cobros con tarjeta.
Docs: https://stripe.com/docs/api
"""
import httpx
import logging
from typing import Dict, Any
from app.services.payments.payment_base import (
    PaymentDriverBase, PaymentCredentials, ChargeResult, PaymentError
)

logger = logging.getLogger("payment.stripe")

STRIPE_API_URL = "https://api.stripe.com/v1"


class StripeDriver(PaymentDriverBase):

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.credentials.secret_key}",
        }

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{STRIPE_API_URL}/balance",
                    headers=self._get_headers(),
                    timeout=10,
                )
                return {
                    "connected": response.status_code == 200,
                    "gateway": "stripe",
                    "environment": self.credentials.environment,
                }
        except Exception as e:
            return {"connected": False, "gateway": "stripe", "error": str(e)}

    async def create_charge(
        self, amount, description, customer_name="", customer_email="",
        customer_phone="", reference_id="", metadata=None,
    ) -> ChargeResult:
        try:
            # Stripe usa centavos
            amount_cents = int(amount * 100)

            # Crear Checkout Session (genera link de pago)
            payload = {
                "payment_method_types[]": "card",
                "line_items[0][price_data][currency]": self.credentials.currency.lower(),
                "line_items[0][price_data][product_data][name]": description,
                "line_items[0][price_data][unit_amount]": str(amount_cents),
                "line_items[0][quantity]": "1",
                "mode": "payment",
                "success_url": "https://ejemplo.com/pago-exitoso",
                "cancel_url": "https://ejemplo.com/pago-cancelado",
                "customer_email": customer_email or "",
                "metadata[reference_id]": reference_id,
                "metadata[customer_name]": customer_name,
                "metadata[customer_phone]": customer_phone,
            }

            if metadata:
                for k, v in metadata.items():
                    payload[f"metadata[{k}]"] = str(v)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{STRIPE_API_URL}/checkout/sessions",
                    data=payload,
                    headers=self._get_headers(),
                    timeout=15,
                )
                data = response.json()

                if response.status_code == 200:
                    return ChargeResult(
                        success=True,
                        charge_id=data.get("id", ""),
                        payment_url=data.get("url", ""),
                        status=data.get("payment_status", "unpaid"),
                        raw_response=data,
                    )
                return ChargeResult(
                    success=False,
                    error=data.get("error", {}).get("message", "Error Stripe")
                )
        except Exception as e:
            return ChargeResult(success=False, error=str(e))

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{STRIPE_API_URL}/checkout/sessions/{charge_id}",
                    headers=self._get_headers(),
                    timeout=10,
                )
                return response.json()
        except Exception as e:
            raise PaymentError(f"Error Stripe: {e}")

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        # Stripe usa Stripe-Signature header + HMAC
        # En producción implementar verificación completa
        return True

    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        obj = body.get("data", {}).get("object", {})
        return {
            "event": body.get("type", ""),
            "charge_id": obj.get("id", ""),
            "status": obj.get("payment_status", ""),
            "amount": obj.get("amount_total", 0) / 100,
            "reference": obj.get("payment_intent", ""),
        }