"""
Sistema ISP - Driver: OpenPay
API de OpenPay (BBVA) para cobros con tarjeta, SPEI y tiendas.
Docs: https://www.openpay.mx/docs/
"""
import httpx
import base64
import logging
from typing import Dict, Any
from app.services.payments.payment_base import (
    PaymentDriverBase, PaymentCredentials, ChargeResult, PaymentError
)

logger = logging.getLogger("payment.openpay")

OPENPAY_PROD_URL = "https://api.openpay.mx/v1"
OPENPAY_SANDBOX_URL = "https://sandbox-api.openpay.mx/v1"


class OpenPayDriver(PaymentDriverBase):

    @property
    def base_url(self) -> str:
        base = OPENPAY_SANDBOX_URL if self.is_sandbox else OPENPAY_PROD_URL
        return f"{base}/{self.credentials.merchant_id}"

    def _get_headers(self) -> dict:
        encoded = base64.b64encode(f"{self.credentials.secret_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/charges",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10,
                )
                return {
                    "connected": response.status_code == 200,
                    "gateway": "openpay",
                    "environment": self.credentials.environment,
                    "merchant_id": self.credentials.merchant_id,
                }
        except Exception as e:
            return {"connected": False, "gateway": "openpay", "error": str(e)}

    async def create_charge(
        self, amount, description, customer_name="", customer_email="",
        customer_phone="", reference_id="", metadata=None,
    ) -> ChargeResult:
        try:
            payload = {
                "method": "store",  # store = OXXO/tiendas, bank_account = SPEI, card = tarjeta
                "amount": amount,
                "currency": self.credentials.currency,
                "description": description,
                "order_id": reference_id or None,
                "customer": {
                    "name": customer_name or "Cliente",
                    "email": customer_email or "cliente@ejemplo.com",
                    "phone_number": customer_phone or "0000000000",
                },
                "send_email": True if customer_email else False,
                "confirm": False,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=15,
                )
                data = response.json()

                if response.status_code in (200, 201):
                    payment_method = data.get("payment_method", {})
                    return ChargeResult(
                        success=True,
                        charge_id=data.get("id", ""),
                        payment_url=payment_method.get("url", ""),
                        status=data.get("status", "in_progress"),
                        reference=payment_method.get("reference", ""),
                        barcode_url=payment_method.get("barcode_url", ""),
                        expires_at=data.get("due_date", ""),
                        raw_response=data,
                    )
                return ChargeResult(
                    success=False,
                    error=data.get("description", "Error OpenPay")
                )
        except Exception as e:
            return ChargeResult(success=False, error=str(e))

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/charges/{charge_id}",
                    headers=self._get_headers(),
                    timeout=10,
                )
                return response.json()
        except Exception as e:
            raise PaymentError(f"Error OpenPay: {e}")

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        return True

    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        transaction = body.get("transaction", {})
        return {
            "event": body.get("type", ""),
            "charge_id": transaction.get("id", ""),
            "status": transaction.get("status", ""),
            "amount": transaction.get("amount", 0),
            "reference": transaction.get("payment_method", {}).get("reference", ""),
        }