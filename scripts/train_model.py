import os
import logging
import MetaTrader5 as mt5
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
MODEL_PATH = "models/rf_classifier_v1.pkl"
FEATURE_COLS =['returns', 'hl_range', 'sma_dist']

def main():
    if not mt5.initialize():
        logger.error("MT5 falló")
        return

    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 3000)
        if rates is None: return

        df = pd.DataFrame(rates)
        df['returns'] = df['close'] - df['open']
        df['hl_range'] = df['high'] - df['low']
        df['sma_dist'] = df['close'] - df['close'].rolling(20).mean()

        df['future_range'] = (df['high'].shift(-1) - df['low'].shift(-1))
        df['range_ma_20'] = df['hl_range'].rolling(20).mean()
        df['target'] = (df['future_range'] > df['range_ma_20']).astype(int)

        df = df.dropna().reset_index(drop=True)
        X, y = df[FEATURE_COLS], df['target']

        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
        model.fit(X_train, y_train)

        print("\nReporte Test Set:")
        print(classification_report(y_test, model.predict(X_test)))

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        print(f"Modelo guardado en {MODEL_PATH}")

    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
