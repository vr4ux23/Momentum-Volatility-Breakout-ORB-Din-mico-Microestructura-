import logging
import threading
import queue
import time
import psycopg2
from psycopg2 import extras
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class PostgresLogger:
    def __init__(self, db_config: Dict[str, str], queue_size: int = 1000):
        self.db_config = db_config
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("PostgresLogger inicializado. Worker thread iniciado.")

    def _get_connection(self) -> Optional[psycopg2.extensions.connection]:
        try:
            return psycopg2.connect(
                host=self.db_config.get('DB_HOST', 'localhost'),
                port=self.db_config.get('DB_PORT', '5432'),
                user=self.db_config.get('DB_USER'),
                password=self.db_config.get('DB_PASS'),
                dbname=self.db_config.get('DB_NAME')
            )
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            return None

    def log_trade(self, data: Dict[str, Any]) -> None:
        try:
            self.log_queue.put_nowait({'type': 'trade', 'data': data})
        except queue.Full:
            pass

    def log_microstructure(self, data: Dict[str, Any]) -> None:
        try:
            if self.log_queue.qsize() < self.log_queue.maxsize // 2:
                self.log_queue.put_nowait({'type': 'micro', 'data': data})
        except queue.Full:
            pass

    def _worker_loop(self) -> None:
        conn = None
        batch = {'trade': [], 'micro':[]}
        BATCH_SIZE = 10

        while not self.stop_event.is_set():
            try:
                try:
                    item = self.log_queue.get(timeout=1.0)
                    batch[item['type']].append(item['data'])
                except queue.Empty:
                    if any(batch.values()) and conn:
                        self._flush_batch(conn, batch)
                        batch = {'trade': [], 'micro':[]}
                    continue

                if len(batch[item['type']]) >= BATCH_SIZE:
                    if conn is None or conn.closed:
                        conn = self._get_connection()
                    if conn:
                        self._flush_batch(conn, batch)
                        batch[item['type']] =[]
            except Exception as e:
                logger.error(f"Error en worker de logs: {e}")
                time.sleep(2)

        if conn:
            conn.close()

    def _flush_batch(self, conn, batch):
        try:
            with conn.cursor() as cur:
                if batch['trade']:
                    sql = "INSERT INTO trade_logs (ticket, symbol, action, volume, entry_price, sl, tp, pnl, timestamp, reason) VALUES %s"
                    vals =[(d.get('ticket'), d.get('symbol'), d.get('action'), d.get('volume'), d.get('entry_price'), d.get('sl'), d.get('tp'), d.get('pnl'), d.get('timestamp'), d.get('reason')) for d in batch['trade']]
                    extras.execute_values(cur, sql, vals)
                if batch['micro']:
                    sql = "INSERT INTO microstructure_logs (symbol, timestamp, tick_velocity, buy_volume, sell_volume, delta) VALUES %s"
                    vals =[(d.get('symbol'), d.get('timestamp'), d.get('tick_velocity'), d.get('buy_volume'), d.get('sell_volume'), d.get('delta')) for d in batch['micro']]
                    extras.execute_values(cur, sql, vals)
            conn.commit()
        except Exception:
            conn.rollback()

    def stop(self) -> None:
        self.stop_event.set()
        self.worker_thread.join(timeout=5)
