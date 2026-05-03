import logging
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class PositionManager:
    """Gestiona el ciclo de vida de las posiciones abiertas (Trailing Stop ATR)."""

    def __init__(self, atr_period: int = 14, atr_multiplier: float = 2.0, timeframe: int = mt5.TIMEFRAME_M5):
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.timeframe = timeframe
        self.cached_atr: Optional[float] = None
        self.last_atr_time: int = 0

    def _calculate_atr(self, symbol: str) -> Optional[float]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, self.timeframe, 0, 1)
            if rates is None or len(rates) == 0: return self.cached_atr

            bar_time = rates[0]['time']
            if bar_time == self.last_atr_time and self.cached_atr is not None:
                return self.cached_atr

            full_rates = mt5.copy_rates_from_pos(symbol, self.timeframe, 0, self.atr_period + 10)
            if full_rates is None or len(full_rates) < self.atr_period:
                 return self.cached_atr

            df = pd.DataFrame(full_rates)
            high = df['high']
            low = df['low']
            close = df['close']

            tr1 = high.shift(1) - low.shift(1)
            tr2 = np.abs(high.shift(1) - close)
            tr3 = np.abs(low.shift(1) - close)
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=self.atr_period).mean().iloc[-1]

            self.cached_atr = float(atr)
            self.last_atr_time = bar_time
            return self.cached_atr
        except Exception as e:
            logger.error(f"Error calculando ATR: {e}")
            return self.cached_atr

    def update_trailing_stop(self, symbol: str, ticket: int, position_type: int) -> bool:
        position = mt5.position_get(ticket=ticket)
        if not position: return False

        current_sl = position[0].sl
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return False

        current_price = tick.bid if position_type == mt5.ORDER_TYPE_SELL else tick.ask
        atr = self._calculate_atr(symbol)
        if atr is None or atr <= 0: return False

        if position_type == mt5.ORDER_TYPE_BUY:
            new_sl = current_price - (atr * self.atr_multiplier)
            if new_sl <= current_sl: return True
        else:
            new_sl = current_price + (atr * self.atr_multiplier)
            if current_sl != 0.0 and new_sl >= current_sl: return True

        sym_info = mt5.symbol_info(symbol)
        if abs(new_sl - current_sl) < (sym_info.trade_tick_size * 2): return True

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": float(new_sl),
            "tp": float(position[0].tp)
        }

        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Trailing Stop de {ticket} actualizado a {new_sl}")
            return True
        return False
