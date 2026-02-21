"""
Sistema ISP - Driver: Mercado Pago
API de Mercado Pago para cobros en LATAM.
Docs: https://www.mercadopago.com.mx/developers/
"""
import httpx
import logging
from typing import Dict, Any
from app.services.payments.payment_base import (
    PaymentDriverBase, PaymentCredentials, ChargeResult, PaymentError
)

logger = logging.getLogger("payment.mercadopago")

MERCADOPAGO_API_URL = "https://api.mercadopago.com"


class MercadoPagoDriver(PaymentDriverBase):

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.credentials.api_key}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{MERCADOPAGO_API_URL}/users/me",
                    headers=self._get_headers(),
                    timeout=10,
                )
                data = response.json()
                return {
                    "connected": response.status_code == 200,
                    "gateway": "mercadopago",
                    "environment": self.credentials.environment,
                    "account": data.get("email", ""),
                }
        except Exception as e:
            return {"connected": False, "gateway": "mercadopago", "error": str(e)}

    async def create_charge(
        self, amount, description, customer_name="", customer_email="",
        customer_phone="", reference_id="", metadata=None,
    ) -> ChargeResult:
        try:
            # Crear preferencia de pago (genera link)
            payload = {
                "items": [{
                    "title": description,
                    "quantity": 1,
                    "unit_price": amount,
                    "currency_id": self.credentials.currency,
                }],
                "payer": {
                    "name": customer_name or "Cliente",
                    "email": customer_email or "cliente@ejemplo.com",
                },
                "payment_methods": {
                    "excluded_payment_types": [],
                    "installments": 1,
                },
                "external_reference": reference_id,
                "notification_url": "",  # Se configura en el dashboard de MP
                "auto_return": "approved",
                "back_urls": {
                    "success": "https://ejemplo.com/pago-exitoso",
                    "failure": "https://ejemplo.com/pago-fallido",
                    "pending": "https://ejemplo.com/pago-pendiente",
                },
                "metadata": metadata or {},
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{MERCADOPAGO_API_URL}/checkout/preferences",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=15,
                )
                data = response.json()

                if response.status_code in (200, 201):
                    return ChargeResult(
                        success=True,
                        charge_id=data.get("id", ""),
                        payment_url=data.get("init_point", ""),  # Link de pago
                        status="pending",
                        raw_response=data,
                    )
                return ChargeResult(
                    success=False,
                    error=data.get("message", "Error Mercado Pago")
                )
        except Exception as e:
            return ChargeResult(success=False, error=str(e))

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{MERCADOPAGO_API_URL}/v1/payments/{charge_id}",
                    headers=self._get_headers(),
                    timeout=10,
                )
                return response.json()
        except Exception as e:
            raise PaymentError(f"Error Mercado Pago: {e}")

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        return True

    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        data = body.get("data", {})
        return {
            "event": body.get("type", ""),
            "charge_id": data.get("id", ""),
            "status": "",
            "amount": 0,
            "reference": "",
            "action": body.get("action", ""),
        }