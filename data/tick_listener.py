import time
import logging
import datetime
from typing import Optional, Dict, Any
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TickAnalyzer:
    def __init__(self):
        logger.info("TickAnalyzer inicializado.")

    def ensure_symbol(self, symbol: str) -> bool:
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
            return True
        except Exception as e:
            logger.error(f"Excepción al verificar/seleccionar símbolo {symbol}: {e}")
            return False

    def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return {
                "bid": tick.bid, "ask": tick.ask, "last": tick.last,
                "volume": tick.volume, "time_msc": tick.time_msc,
                "time": datetime.datetime.fromtimestamp(tick.time)
            }
        except Exception:
            return None

    def get_microstructure_features(self, symbol: str, lookback_seconds: int = 15) -> Dict[str, Any]:
        default_result = {"tick_velocity": 0, "buy_volume": 0.0, "sell_volume": 0.0, "delta": 0.0}
        try:
            current_tick = mt5.symbol_info_tick(symbol)
            if current_tick is None: return default_result

            broker_time_dt = datetime.datetime.fromtimestamp(current_tick.time)
            ticks_data = mt5.copy_ticks_from(symbol, broker_time_dt, 2000, mt5.COPY_TICKS_ALL)

            if ticks_data is None or len(ticks_data) == 0: return default_result

            df = pd.DataFrame(ticks_data)
            if df.empty: return default_result

            df['time_dt'] = pd.to_datetime(df['time_msc'], unit='ms', utc=True).dt.tz_localize(None)
            latest_tick_time = df['time_dt'].max()
            cutoff_time = latest_tick_time - pd.Timedelta(seconds=lookback_seconds)

            df_filtered = df[df['time_dt'] >= cutoff_time].copy()
            if df_filtered.empty: return default_result

            tick_velocity = len(df_filtered)
            mask_buy = (df_filtered['flags'] & mt5.TICK_FLAG_BUY) > 0
            mask_sell = (df_filtered['flags'] & mt5.TICK_FLAG_SELL) > 0

            buy_volume = float(df_filtered.loc[mask_buy, 'volume'].sum())
            sell_volume = float(df_filtered.loc[mask_sell, 'volume'].sum())
            delta = buy_volume - sell_volume

            return {
                "tick_velocity": tick_velocity, "buy_volume": buy_volume,
                "sell_volume": sell_volume, "delta": delta
            }
        except Exception as e:
            logger.error(f"Error calculando microestructura: {e}")
            return default_result
