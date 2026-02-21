"""
Sistema ISP - OLT Factory
Crea la instancia correcta del driver según la marca de OLT.
Patrón Factory: una sola función que retorna el driver apropiado.
"""
import logging
from app.services.olt.olt_base import OltCredentials, OltDriverBase, OltError
from app.services.olt.drivers.zte_driver import ZteDriver
from app.services.olt.drivers.vsol_driver import VsolDriver

logger = logging.getLogger("olt_factory")

# Registro de drivers disponibles
DRIVERS = {
    "zte": ZteDriver,
    "vsol": VsolDriver,
    # Futuros drivers:
    # "huawei": HuaweiDriver,
    # "fiberhome": FiberHomeDriver,
}

# Aliases de marcas (para que el operador no tenga que escribir exacto)
BRAND_ALIASES = {
    "zte": "zte",
    "zxa10": "zte",
    "c300": "zte",
    "c320": "zte",
    "c600": "zte",
    "vsol": "vsol",
    "v-sol": "vsol",
    "huawei": "huawei",
    "hw": "huawei",
    "ma5608t": "huawei",
    "ma5800": "huawei",
    "fiberhome": "fiberhome",
    "fh": "fiberhome",
}


def get_olt_driver(credentials: OltCredentials) -> OltDriverBase:
    """
    Crea y retorna el driver correcto según la marca de la OLT.
    
    Args:
        credentials: Credenciales con brand definido
    
    Returns:
        Instancia del driver correspondiente
    
    Raises:
        OltError: Si la marca no tiene driver disponible
    """
    brand = credentials.brand.lower().strip()

    # Buscar en aliases
    normalized = BRAND_ALIASES.get(brand, brand)

    driver_class = DRIVERS.get(normalized)
    if not driver_class:
        available = ", ".join(DRIVERS.keys())
        raise OltError(
            f"No hay driver disponible para marca '{credentials.brand}'. "
            f"Marcas soportadas: {available}"
        )

    logger.info(f"Creando driver OLT: {normalized} para {credentials.host}")
    return driver_class(credentials)


def get_supported_brands() -> list:
    """Retorna lista de marcas soportadas."""
    return list(DRIVERS.keys())