import logging
import datetime
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class TradingScheduler:
    """Reloj maestro basado estrictamente en la hora del servidor MT5."""

    def __init__(self, config: dict):
        self.schedule = config.get('schedule', {})
        self.start_hour = self.schedule.get('start_hour', 8)
        self.end_hour = self.schedule.get('end_hour', 17)

    def _get_broker_time(self, symbol: str) -> datetime.datetime:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return datetime.datetime.fromtimestamp(tick.time)

    def is_trading_window_active(self, symbol: str) -> bool:
        broker_time = self._get_broker_time(symbol)
        if self.start_hour <= self.end_hour:
            return self.start_hour <= broker_time.hour < self.end_hour
        else:
            return broker_time.hour >= self.start_hour or broker_time.hour < self.end_hour

    def minutes_to_next_window(self, symbol: str) -> int:
        if self.is_trading_window_active(symbol):
            return 0
        broker_time = self._get_broker_time(symbol)
        target = broker_time.replace(hour=self.start_hour, minute=0, second=0)
        if broker_time.hour >= self.start_hour:
            target += datetime.timedelta(days=1)
        return int((target - broker_time).total_seconds() / 60)
