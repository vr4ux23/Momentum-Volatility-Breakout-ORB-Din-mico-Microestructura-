import logging
import os
from typing import Optional, Dict, Any
import MetaTrader5 as mt5
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

class MLTradeFilter:
    """Semáforo defensivo HFT con Caché O(1) de inferencia."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('ml_filter', {})
        self.model_path = self.config.get('model_path', 'models/rf_classifier_v1.pkl')
        self.min_probability = self.config.get('min_probability_threshold', 0.60)
        self.window_size = self.config.get('features_window_size', 20)

        self.model = None
        self.cached_predictions: Dict[str, bool] = {}

        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Modelo ML cargado: {self.model_path}")
            except Exception as e:
                logger.error(f"Error cargando modelo: {e}")
        else:
            logger.warning(f"Modelo no encontrado en {self.model_path}. Modo FAIL-OPEN.")

    def _extract_features(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, self.window_size)
            if rates is None or len(rates) < self.window_size: return None

            df = pd.DataFrame(rates)
            df['returns'] = df['close'] - df['open']
            df['hl_range'] = df['high'] - df['low']
            df['sma_dist'] = df['close'] - df['close'].mean()

            return df[['returns', 'hl_range', 'sma_dist']].iloc[[-1]].reset_index(drop=True)
        except Exception as e:
            logger.error(f"Error ML features: {e}")
            return None

    def update_predictions(self, symbol: str) -> None:
        if self.model is None: return

        features = self._extract_features(symbol)
        if features is None: return

        try:
            prob_success = self.model.predict_proba(features)[0][1]
            self.cached_predictions[symbol] = prob_success >= self.min_probability
            logger.info(f"ML Caché Actualizada para {symbol}: {self.cached_predictions[symbol]}")
        except Exception as e:
            logger.error(f"Error Inferencia ML: {e}")

    def is_trade_allowed(self, symbol: str) -> bool:
        if self.model is None: return True # Fail-Open
        return self.cached_predictions.get(symbol, True)
