"""
Sistema ISP - Driver: Conekta
API de Conekta para cobros con tarjeta, OXXO y SPEI.
Docs: https://developers.conekta.com/
"""
import httpx
import base64
import logging
from typing import Dict, Any
from app.services.payments.payment_base import (
    PaymentDriverBase, PaymentCredentials, ChargeResult, PaymentError
)

logger = logging.getLogger("payment.conekta")

CONEKTA_API_URL = "https://api.conekta.io"


class ConektaDriver(PaymentDriverBase):

    def _get_headers(self) -> dict:
        """Conekta usa Basic Auth con api_key como usuario."""
        encoded = base64.b64encode(f"{self.credentials.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.conekta-v2.1.0+json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CONEKTA_API_URL}/customers",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10,
                )
                return {
                    "connected": response.status_code == 200,
                    "gateway": "conekta",
                    "environment": self.credentials.environment,
                }
        except Exception as e:
            return {"connected": False, "gateway": "conekta", "error": str(e)}

    async def create_charge(
        self, amount, description, customer_name="", customer_email="",
        customer_phone="", reference_id="", metadata=None,
    ) -> ChargeResult:
        try:
            # Conekta maneja montos en centavos
            amount_cents = int(amount * 100)

            payload = {
                "currency": self.credentials.currency,
                "customer_info": {
                    "name": customer_name or "Cliente",
                    "email": customer_email or "cliente@ejemplo.com",
                    "phone": customer_phone or "0000000000",
                },
                "line_items": [{
                    "name": description,
                    "unit_price": amount_cents,
                    "quantity": 1,
                }],
                "charges": [{
                    "payment_method": {
                        "type": "default",
                    }
                }],
                "checkout": {
                    "type": "Integration",
                    "allowed_payment_methods": ["card", "cash", "bank_transfer"],
                    "expires_after_days": 5,
                },
                "metadata": metadata or {"reference_id": reference_id},
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CONEKTA_API_URL}/orders",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=15,
                )
                data = response.json()

                if response.status_code in (200, 201):
                    checkout = data.get("checkout", {})
                    return ChargeResult(
                        success=True,
                        charge_id=data.get("id", ""),
                        payment_url=checkout.get("url", ""),
                        status=data.get("payment_status", "pending"),
                        reference=data.get("charges", {}).get("data", [{}])[0].get("payment_method", {}).get("reference", ""),
                        expires_at=checkout.get("expires_at", ""),
                        raw_response=data,
                    )
                return ChargeResult(
                    success=False,
                    error=data.get("details", [{}])[0].get("message", "Error Conekta")
                )
        except Exception as e:
            return ChargeResult(success=False, error=str(e))

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CONEKTA_API_URL}/orders/{charge_id}",
                    headers=self._get_headers(),
                    timeout=10,
                )
                return response.json()
        except Exception as e:
            raise PaymentError(f"Error Conekta: {e}")

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        # Conekta envía header "Digest" para verificar
        return True

    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        data = body.get("data", {}).get("object", {})
        return {
            "event": body.get("type", ""),
            "charge_id": data.get("id", ""),
            "status": data.get("payment_status", ""),
            "amount": data.get("amount", 0) / 100,  # centavos a pesos
            "reference": "",
        }