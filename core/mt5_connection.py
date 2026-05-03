import logging
import os
import time
import MetaTrader5 as mt5
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class MT5Connector:
    """Gestiona la conexión resiliente con el terminal MetaTrader 5."""

    def connect(self, max_retries: int = 5) -> bool:
        mt5_path = os.getenv('MT5_PATH')
        init_kwargs = {}
        if mt5_path:
            init_kwargs['path'] = mt5_path
        retries = 0
        while retries < max_retries:
            if mt5.initialize(**init_kwargs):
                logger.info("Conexión MT5 establecida correctamente.")
                return True
            retries += 1
            logger.warning(f"Fallo al conectar MT5. Intento {retries}/{max_retries}")
            time.sleep(2)
        logger.error("No se pudo conectar a MT5 después de múltiples intentos.")
        return False

    def is_connected(self) -> bool:
        info = mt5.terminal_info()
        return info is not None and info.connected

    def get_account_info(self) -> Optional[Dict[str, float]]:
        acc_info = mt5.account_info()
        if acc_info is None:
            logger.error(f"Fallo al obtener info de cuenta: {mt5.last_error()}")
            return None
        return {
            "balance": acc_info.balance,
            "equity": acc_info.equity,
            "margin_free": acc_info.margin_free
        }

    def disconnect(self):
        mt5.shutdown()
        logger.info("Conexión MT5 cerrada.")
