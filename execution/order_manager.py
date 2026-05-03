import logging
from typing import Optional, Dict
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class OrderManager:
    def __init__(self, magic_number: int, max_slippage_points: int):
        self.magic = magic_number
        self.slip = max_slippage_points

    def _get_filling_mode(self, symbol: str) -> int:
        info = mt5.symbol_info(symbol)
        if not info: return mt5.ORDER_FILLING_RETURN
        if info.filling_mode & mt5.SYMBOL_FILLING_FOK: return mt5.ORDER_FILLING_FOK
        if info.filling_mode & mt5.SYMBOL_FILLING_IOC: return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    def send_market_order(self, symbol: str, order_type: int, volume: float, sl: float, tp: float, comment: str) -> Optional[Dict]:
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return None

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": self.slip,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(symbol),
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else mt5.last_error()
            logger.error(f"Fallo envío orden: {err}")
            return None

        logger.info(f"Orden ejecutada. Ticket: {result.order}")
        return {"ticket": result.order, "price": result.price, "volume": result.volume}
