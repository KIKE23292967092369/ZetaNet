"""
Sistema ISP - Driver: TapiPay
API de TapiPay para cobros SPEI/transferencia.
"""
import httpx
import logging
from typing import Dict, Any
from app.services.payments.payment_base import (
    PaymentDriverBase, PaymentCredentials, ChargeResult, PaymentError
)

logger = logging.getLogger("payment.tapipay")

TAPIPAY_BASE_URL = "https://api.tapipay.com/v1"
TAPIPAY_SANDBOX_URL = "https://sandbox.tapipay.com/v1"


class TapiPayDriver(PaymentDriverBase):

    @property
    def base_url(self) -> str:
        return TAPIPAY_SANDBOX_URL if self.is_sandbox else TAPIPAY_BASE_URL

    async def test_connection(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/account",
                    headers={"Authorization": f"Bearer {self.credentials.api_key}"},
                    timeout=10,
                )
                return {
                    "connected": response.status_code == 200,
                    "gateway": "tapipay",
                    "environment": self.credentials.environment,
                }
        except Exception as e:
            return {"connected": False, "gateway": "tapipay", "error": str(e)}

    async def create_charge(
        self, amount, description, customer_name="", customer_email="",
        customer_phone="", reference_id="", metadata=None,
    ) -> ChargeResult:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "amount": amount,
                    "description": description,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "reference": reference_id,
                    "metadata": metadata or {},
                }
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.credentials.api_key}"},
                    timeout=15,
                )
                data = response.json()

                if response.status_code in (200, 201):
                    return ChargeResult(
                        success=True,
                        charge_id=data.get("id", ""),
                        payment_url=data.get("payment_url", ""),
                        status=data.get("status", "pending"),
                        reference=data.get("reference", ""),
                        raw_response=data,
                    )
                return ChargeResult(success=False, error=data.get("message", "Error TapiPay"))
        except Exception as e:
            return ChargeResult(success=False, error=str(e))

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/charges/{charge_id}",
                    headers={"Authorization": f"Bearer {self.credentials.api_key}"},
                    timeout=10,
                )
                return response.json()
        except Exception as e:
            raise PaymentError(f"Error TapiPay: {e}")

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        # TapiPay webhook verification
        return True

    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        return {
            "event": body.get("event", ""),
            "charge_id": body.get("data", {}).get("id", ""),
            "status": body.get("data", {}).get("status", ""),
            "amount": body.get("data", {}).get("amount", 0),
            "reference": body.get("data", {}).get("reference", ""),
        }