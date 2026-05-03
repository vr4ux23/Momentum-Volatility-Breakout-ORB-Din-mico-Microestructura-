import logging
from typing import Dict, Any
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class RiskManager:
    """Escudo de Prop Firm (Drawdown) y gestión de lotaje por Tiers de Riesgo."""

    def __init__(self, config: Dict[str, Any], connector):
        self.config = config.get('risk_management', {})
        self.connector = connector
        self.max_daily_drawdown_pct = self.config.get('max_daily_drawdown_pct', 4.0)
        self.calc_on_equity = self.config.get('calc_drawdown_on_equity', True)
        self.tiers = self.config.get('risk_tiers_usd', {1: 50, 2: 100, 3: 200})

        self.start_of_day_balance = 0.0
        self.start_of_day_equity = 0.0

    def update_start_of_day_metrics(self):
        info = self.connector.get_account_info()
        if info:
            self.start_of_day_balance = info['balance']
            self.start_of_day_equity = info['equity']
            logger.info(f"Métricas diarias reseteadas: Balance={self.start_of_day_balance}, Equity={self.start_of_day_equity}")

    def check_daily_drawdown(self) -> bool:
        """Retorna False si se ha violado el Drawdown Máximo Diario."""
        info = self.connector.get_account_info()
        if not info or self.start_of_day_balance == 0:
            return True # Asumimos seguro si no hay datos

        current_val = info['equity'] if self.calc_on_equity else info['balance']
        reference_val = self.start_of_day_equity if self.calc_on_equity else self.start_of_day_balance

        drawdown_pct = ((reference_val - current_val) / reference_val) * 100

        if drawdown_pct >= self.max_daily_drawdown_pct:
            logger.critical(f"DRAWDOWN DIARIO ALCANZADO: {drawdown_pct:.2f}%")
            return False
        return True

    def calculate_position_size(self, symbol: str, sl_distance_price: float, tier: int = 1) -> float:
        """Calcula el lotaje basado en el riesgo absoluto en USD y la distancia del SL en precio."""
        risk_usd = self.tiers.get(tier, self.tiers[1])
        sym_info = mt5.symbol_info(symbol)

        if not sym_info or sl_distance_price <= 0: return 0.0

        tick_size = sym_info.trade_tick_size
        tick_value = sym_info.trade_tick_value

        if tick_size == 0 or tick_value == 0: return 0.0

        sl_ticks = sl_distance_price / tick_size
        loss_per_lot = sl_ticks * tick_value

        if loss_per_lot == 0: return 0.0

        raw_lot = risk_usd / loss_per_lot
        step = sym_info.volume_step
        min_vol = sym_info.volume_min
        max_vol = sym_info.volume_max

        lot_size = round(raw_lot / step) * step
        lot_size = max(min_vol, min(lot_size, max_vol))

        return round(lot_size, 2)
