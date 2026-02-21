"""
Sistema ISP - Payment Base (Clase Abstracta)
Define la interfaz que todos los drivers de pago deben implementar.
Cada pasarela (TapiPay, Conekta, Stripe, OpenPay, MercadoPago)
implementa estos métodos con sus APIs específicas.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("payment_base")


@dataclass
class PaymentCredentials:
    """Credenciales de conexión a una pasarela de pago."""
    gateway_type: str
    api_key: str
    secret_key: str = ""
    merchant_id: str = ""
    webhook_secret: str = ""
    currency: str = "MXN"
    environment: str = "sandbox"         # sandbox / production


@dataclass
class ChargeResult:
    """Resultado de crear un cobro."""
    success: bool
    charge_id: str = ""
    payment_url: str = ""                # Link para que el cliente pague
    status: str = ""                     # pending, paid, failed
    reference: str = ""                  # Referencia OXXO/SPEI
    barcode_url: str = ""                # Código de barras OXXO
    expires_at: str = ""
    error: str = ""
    raw_response: dict = None

    def __post_init__(self):
        if self.raw_response is None:
            self.raw_response = {}


class PaymentError(Exception):
    """Error de comunicación con pasarela de pago."""
    pass


class PaymentDriverBase(ABC):
    """
    Clase base abstracta para drivers de pasarelas de pago.
    Cada pasarela implementa estos métodos con su API específica.
    """

    def __init__(self, credentials: PaymentCredentials):
        self.credentials = credentials

    @property
    def gateway_type(self) -> str:
        return self.credentials.gateway_type

    @property
    def is_sandbox(self) -> bool:
        return self.credentials.environment == "sandbox"

    # ================================================================
    # CONEXIÓN
    # ================================================================

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con la pasarela.
        Returns: {"connected": bool, "gateway": str, "environment": str, ...}
        """
        pass

    # ================================================================
    # COBROS
    # ================================================================

    @abstractmethod
    async def create_charge(
        self,
        amount: float,
        description: str,
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        reference_id: str = "",
        metadata: dict = None,
    ) -> ChargeResult:
        """
        Crea un cobro/cargo en la pasarela.
        Retorna un link de pago o referencia.
        
        Args:
            amount: Monto en pesos (ej: 349.00)
            description: "Pago internet marzo 2026"
            customer_name: Nombre del cliente
            customer_email: Email del cliente
            customer_phone: Teléfono del cliente
            reference_id: ID interno (ej: invoice_id)
            metadata: Datos extra
        
        Returns:
            ChargeResult con payment_url, reference, etc.
        """
        pass

    @abstractmethod
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """
        Consulta el estado de un cobro.
        Returns: {"charge_id": str, "status": str, "amount": float, ...}
        """
        pass

    # ================================================================
    # WEBHOOKS
    # ================================================================

    @abstractmethod
    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """
        Verifica que un webhook sea legítimo.
        Cada pasarela tiene su propio método de verificación.
        """
        pass

    @abstractmethod
    def parse_webhook(self, body: dict) -> Dict[str, Any]:
        """
        Parsea el webhook y retorna datos normalizados.
        Returns: {
            "event": "payment.completed",
            "charge_id": "xxx",
            "status": "paid",
            "amount": 349.00,
            "reference": "xxx",
        }
        """
        pass