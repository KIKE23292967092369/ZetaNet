"""
Sistema ISP - Router: Webhooks
Endpoint público para recibir notificaciones de pago de tapipay.
NO requiere autenticación JWT.
"""
from fastapi import APIRouter, Request, HTTPException
import logging

from app.database import AsyncSessionLocal
from app.services.billing_service import process_tapipay_payment

logger = logging.getLogger("webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/tapipay")
async def tapipay_webhook(request: Request):
    """
    Webhook de tapipay.
    Recibe notificación de pago y procesa automáticamente.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "JSON inválido")

    logger.info(f"Webhook tapipay recibido: {body}")

    async with AsyncSessionLocal() as db:
        try:
            result = await process_tapipay_payment(db, body)
            logger.info(f"Webhook procesado: {result}")
            return {"status": "ok", "detail": result}
        except Exception as e:
            logger.error(f"Error procesando webhook: {e}")
            return {"status": "error", "detail": str(e)}