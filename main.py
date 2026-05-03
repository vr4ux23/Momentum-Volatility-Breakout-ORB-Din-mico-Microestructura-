import os
import sys
import time
import logging
import yaml
from dotenv import load_dotenv
import MetaTrader5 as mt5

from core.mt5_connection import MT5Connector
from core.scheduler import TradingScheduler
from data.tick_listener import TickAnalyzer
from data.pre_open_buffer import PreOpenBoxCalculator
from data.pg_logger import PostgresLogger
from execution.order_manager import OrderManager
from execution.position_manager import PositionManager
from risk.compliance_layer import RiskManager
from ml.ml_filter import MLTradeFilter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        load_dotenv()
        with open("config/config.yaml", 'r') as f:
            self.config = yaml.safe_load(f)

        self.connector = MT5Connector()
        if not self.connector.connect(): sys.exit(1)

        self.scheduler = TradingScheduler(self.config)
        self.tick_analyzer = TickAnalyzer()
        self.box_calculator = PreOpenBoxCalculator()
        self.risk_manager = RiskManager(self.config, self.connector)

        self.order_manager = OrderManager(self.config['execution']['magic_number'], self.config['execution']['max_slippage_points'])
        self.position_manager = PositionManager(timeframe=mt5.TIMEFRAME_M5, atr_multiplier=self.config['execution']['atr_multiplier_sl'])
        self.ml_filter = MLTradeFilter(self.config)

        db_conf = {
            'DB_HOST': os.getenv('DB_HOST', 'localhost'),
            'DB_PORT': os.getenv('DB_PORT', '5432'),
            'DB_USER': os.getenv('DB_USER', 'postgres'),
            'DB_PASS': os.getenv('DB_PASS', ''),
            'DB_NAME': os.getenv('DB_NAME', 'hft'),
        }
        self.pg_logger = PostgresLogger(db_conf)

        self.running = True
        self.symbol = "EURUSD"
        self.box_levels = None
        self.cooldown_until = 0
        self.last_ml_update = 0

        self.tick_analyzer.ensure_symbol(self.symbol)
        self.risk_manager.update_start_of_day_metrics()

    def run(self):
        while self.running:
            try:
                if not self.connector.is_connected():
                    self.connector.connect()
                    continue

                tick = mt5.symbol_info_tick(self.symbol)
                if tick and tick.time > self.last_ml_update + 3600:
                    self.ml_filter.update_predictions(self.symbol)
                    self.last_ml_update = tick.time

                if not self.scheduler.is_trading_window_active(self.symbol):
                    time.sleep(10)
                    continue

                if not self.risk_manager.check_daily_drawdown():
                    self.running = False
                    break

                current_time_sec = tick.time if tick else 0
                can_trade = current_time_sec >= self.cooldown_until

                if can_trade:
                    if not self.box_levels:
                        self.box_levels = self.box_calculator.calculate_box(self.symbol, 0, 0, 7, 0)

                    if self.box_levels and tick:
                        features = self.tick_analyzer.get_microstructure_features(self.symbol)

                        if tick.ask > self.box_levels['box_high'] and features['delta'] > 0:
                            if self.ml_filter.is_trade_allowed(self.symbol):
                                sl_price = tick.ask - 0.0050
                                vol = self.risk_manager.calculate_position_size(self.symbol, 0.0050, 1)
                                if vol > 0:
                                    res = self.order_manager.send_market_order(self.symbol, mt5.ORDER_TYPE_BUY, vol, sl_price, tick.ask + 0.0100, "Breakout")
                                    if res:
                                        self.cooldown_until = tick.time + 300
                                        self.pg_logger.log_trade({"ticket": res['ticket'], "symbol": self.symbol, "action": "BUY", "volume": vol, "entry_price": res['price'], "sl": sl_price, "tp": tick.ask + 0.0100, "pnl": 0.0, "timestamp": tick.time_msc, "reason": "Breakout"})

                positions = mt5.positions_get(symbol=self.symbol)
                if positions:
                    for pos in positions:
                        if pos.magic == self.order_manager.magic:
                            self.position_manager.update_trailing_stop(pos.symbol, pos.ticket, pos.type)

                time.sleep(0.001)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error loop: {e}")
                time.sleep(1)

        self.pg_logger.stop()
        self.connector.disconnect()

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
