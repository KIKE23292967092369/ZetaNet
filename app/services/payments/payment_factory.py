"""
Sistema ISP - Payment Factory
Selecciona el driver correcto según el tipo de pasarela.
"""
from app.services.payments.payment_base import PaymentCredentials, PaymentDriverBase, PaymentError
from app.services.payments.drivers.tapipay_driver import TapiPayDriver
from app.services.payments.drivers.conekta_driver import ConektaDriver
from app.services.payments.drivers.stripe_driver import StripeDriver
from app.services.payments.drivers.openpay_driver import OpenPayDriver
from app.services.payments.drivers.mercadopago_driver import MercadoPagoDriver


DRIVER_MAP = {
    "tapipay": TapiPayDriver,
    "conekta": ConektaDriver,
    "stripe": StripeDriver,
    "openpay": OpenPayDriver,
    "mercadopago": MercadoPagoDriver,
}


def get_payment_driver(credentials: PaymentCredentials) -> PaymentDriverBase:
    """Crea la instancia del driver según el tipo de pasarela."""
    driver_class = DRIVER_MAP.get(credentials.gateway_type)
    if not driver_class:
        raise PaymentError(
            f"Pasarela '{credentials.gateway_type}' no soportada. "
            f"Opciones: {', '.join(DRIVER_MAP.keys())}"
        )
    return driver_class(credentials)


def get_supported_gateways() -> list:
    """Lista las pasarelas soportadas."""
    return [
        {"type": "tapipay", "name": "TapiPay", "methods": ["SPEI", "transferencia"]},
        {"type": "conekta", "name": "Conekta", "methods": ["tarjeta", "OXXO", "SPEI"]},
        {"type": "stripe", "name": "Stripe", "methods": ["tarjeta", "internacional"]},
        {"type": "openpay", "name": "OpenPay", "methods": ["tarjeta", "SPEI", "tiendas"]},
        {"type": "mercadopago", "name": "Mercado Pago", "methods": ["tarjeta", "transferencia", "efectivo"]},
    ]