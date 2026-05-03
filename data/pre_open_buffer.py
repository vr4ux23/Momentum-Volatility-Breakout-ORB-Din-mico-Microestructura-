import logging
import datetime
import pandas as pd
import MetaTrader5 as mt5
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class PreOpenBoxCalculator:
    """Calcula los niveles máximos y mínimos (Caja Asiática/Pre-Market)."""

    def calculate_box(self, symbol: str, start_hour: int, start_minute: int, end_hour: int, end_minute: int) -> Optional[Dict[str, float]]:
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None: return None

            broker_now = datetime.datetime.fromtimestamp(tick.time)
            start_time = broker_now.replace(hour=start_hour, minute=start_minute, second=0)
            end_time = broker_now.replace(hour=end_hour, minute=end_minute, second=0)

            if broker_now < end_time: return None

            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start_time, end_time)
            if rates is None or len(rates) == 0: return None

            df = pd.DataFrame(rates)
            box_high = float(df['high'].max())
            box_low = float(df['low'].min())

            logger.info(f"Caja calculada para {symbol}: High={box_high}, Low={box_low}")
            return {"box_high": box_high, "box_low": box_low, "box_size": box_high - box_low}
        except Exception as e:
            logger.error(f"Error calculando caja: {e}")
            return None
