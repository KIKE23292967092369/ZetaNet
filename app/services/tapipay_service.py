"""
Sistema ISP - Servicio de Integración tapipay
Maneja autenticación, creación de deudas y links de pago.

Flujo:
  1. Login → obtener accessToken
  2. POST /references → crear deuda mensual
  3. Guardar link de pago y referencia
  4. Webhook notifica cuando cliente paga

URLs:
  Login: https://login.{env}.tapila.cloud/login
  References: https://referenced-payments.{env}.tapila.cloud/references
  Link de pago: https://www.tapipay.la/s/{slug}/portal/{identifier}/debts
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger("tapipay_service")


class TapipayError(Exception):
    """Error de comunicación con tapipay."""
    pass


class TapipayService:
    """
    Cliente para la API de tapipay.
    Maneja autenticación y creación de deudas.
    """

    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        company_code: str,
        company_slug: str,
        environment: str = "homo",
        modality_id_digital: str = "",
        modality_id_cash: str = "",
        identifier_name_digital: str = "",
        identifier_name_cash: str = "",
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.company_code = company_code
        self.company_slug = company_slug
        self.environment = environment
        self.modality_id_digital = modality_id_digital
        self.modality_id_cash = modality_id_cash
        self.identifier_name_digital = identifier_name_digital
        self.identifier_name_cash = identifier_name_cash

        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # URLs
        self.login_url = f"https://login.{environment}.tapila.cloud/login"
        self.references_url = f"https://referenced-payments.{environment}.tapila.cloud/references"

    # ================================================================
    # AUTENTICACIÓN
    # ================================================================

    async def login(self) -> str:
        """
        Inicia sesión en tapipay y obtiene el accessToken.
        El token se cachea para reutilizar en múltiples llamadas.
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.login_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                    },
                    json={
                        "clientUsername": self.username,
                        "password": self.password,
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data["accessToken"]
                    self._token_expires_at = datetime.utcnow() + timedelta(minutes=50)
                    logger.info("Login exitoso en tapipay")
                    return self._access_token

                elif response.status_code == 400:
                    raise TapipayError("Credenciales de tapipay incorrectas")
                else:
                    raise TapipayError(
                        f"Error login tapipay: HTTP {response.status_code} - {response.text}"
                    )

        except httpx.RequestError as e:
            raise TapipayError(f"Error de conexión con tapipay: {e}")

    async def _get_token(self) -> str:
        """Obtiene un token válido, renovando si expiró."""
        if (
            not self._access_token
            or not self._token_expires_at
            or datetime.utcnow() >= self._token_expires_at
        ):
            await self.login()
        return self._access_token

    def _get_headers(self, token: str) -> dict:
        """Headers para llamadas autenticadas."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-authorization-token": token,
        }

    # ================================================================
    # CREAR DEUDA (FACTURA MENSUAL)
    # ================================================================

    async def create_debt(
        self,
        identifier_value: str,
        amount: float,
        client_name: str,
        client_email: str,
        client_phone: str,
        expiration_date: str,
        concept: str = "Servicio de Internet",
        product: str = "Internet",
        external_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una deuda (factura) en tapipay.

        Args:
            identifier_value: ID único del cliente (ej: "CLI-00045")
            amount: Monto en MXN (50-100,000)
            client_name: Nombre completo
            client_email: Email
            client_phone: Teléfono con código país
            expiration_date: "YYYY-MM-DD"
            concept: Concepto del cobro
            product: Nombre del plan

        Returns:
            Dict con tx, mainTx, references, etc.
        """
        token = await self._get_token()

        if not external_request_id:
            external_request_id = str(uuid.uuid4())

        # Construir modalidades de pago
        generation_data = []

        if self.modality_id_digital:
            generation_data.append({
                "modalityId": self.modality_id_digital,
                "identifierName": self.identifier_name_digital,
                "identifierValue": identifier_value,
            })

        if self.modality_id_cash:
            generation_data.append({
                "modalityId": self.modality_id_cash,
                "identifierName": self.identifier_name_cash,
                "identifierValue": None,  # tapipay genera referencia para efectivo
            })

        if not generation_data:
            raise TapipayError(
                "No hay modalidades de pago configuradas. "
                "Configure modality_id_digital y/o modality_id_cash."
            )

        body = {
            "externalRequestId": external_request_id,
            "companyCode": self.company_code,
            "externalClientId": identifier_value,
            "amount": int(amount),
            "currency": "MXN",
            "amountType": "CLOSED",
            "generationData": generation_data,
            "additionalData": [
                {"dataName": "recurringDebt", "dataValue": False},
                {"dataName": "overduePayment", "dataValue": True},
                {"dataName": "allowPartialPayments", "dataValue": True},
                {"dataName": "debtReference", "dataValue": identifier_value},
                {"dataName": "expirationDate", "dataValue": expiration_date},
                {"dataName": "conceptName", "dataValue": concept},
                {"dataName": "productName", "dataValue": product},
                {"dataName": "variable1", "dataValue": concept},
            ],
            "contactData": {
                "name": client_name,
                "email": client_email,
                "phones": [
                    {
                        "phone": client_phone,
                        "primary": True,
                        "description": "MOBILE",
                        "type": "MOBILE",
                    }
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.references_url,
                    headers=self._get_headers(token),
                    json=body,
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(
                        f"Deuda creada en tapipay: {identifier_value} "
                        f"${amount} tx={data.get('tx')}"
                    )
                    return {
                        "success": True,
                        "amount": data.get("amount"),
                        "currency": data.get("currency"),
                        "tx": data.get("tx"),
                        "main_tx": data.get("mainTx"),
                        "references": data.get("references", []),
                        "external_request_id": external_request_id,
                    }

                elif response.status_code == 400:
                    error_data = response.json() if response.text else {}
                    raise TapipayError(f"Error validación tapipay: {error_data}")
                elif response.status_code == 422:
                    raise TapipayError("Empresa temporalmente no disponible en tapipay")
                else:
                    raise TapipayError(
                        f"Error tapipay: HTTP {response.status_code} - {response.text[:300]}"
                    )

        except httpx.RequestError as e:
            raise TapipayError(f"Error de conexión con tapipay: {e}")

    # ================================================================
    # LINK DE PAGO
    # ================================================================

    def get_payment_link(self, identifier_value: str) -> str:
        """
        Link de pago permanente para un cliente.
        Siempre muestra sus deudas pendientes.
        """
        slug = self.company_slug.lower().strip()
        return f"https://www.tapipay.la/s/{slug}/portal/{identifier_value}/debts"

    # ================================================================
    # TEST CONEXIÓN
    # ================================================================

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba credenciales de tapipay."""
        try:
            token = await self.login()
            return {
                "connected": True,
                "environment": self.environment,
                "company_code": self.company_code,
                "token_preview": token[:20] + "..." if token else None,
            }
        except TapipayError as e:
            return {"connected": False, "error": str(e)}