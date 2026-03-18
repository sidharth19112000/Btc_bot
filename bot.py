import ccxt
import pandas as pd
import numpy as np
import requests
import ta
from sklearn.ensemble import RandomForestClassifier
from flask import Flask
import threading
import time
import os

# ====== TELEGRAM SETTINGS ======
TOKEN = os.getenv("8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8")
CHAT_ID = os.getenv("6094849602")

# ====== EXCHANGE ======
exchange = ccxt.binance()

# ====== FLASK APP ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

# ====== TELEGRAM FUNCTION ======
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# ====== GET DATA ======
def get_data(timeframe="15m", limit=200):
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    return df

# ====== FEATURE ENGINEERING ======
def prepare_data(df):
    df['sma5'] = ta.trend.sma_indicator(df['close'], window=5)
    df['sma10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['sma30'] = ta.trend.sma_indicator(df['close'], window=30)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['macd'] = ta.trend.macd_diff(df['close'])
    df['volume_ma'] = df['volume'].rolling(10).mean()

    df = df.dropna()

    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)

    return df

# ====== TRAIN MODEL ======
def train_model(df):
    features = ['sma5','sma10','sma30','rsi','macd','volume']
    X = df[features]
    y = df['target']

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    return model

# ====== SIGNAL GENERATOR ======
def generate_signal():
    df = get_data()
    df = prepare_data(df)

    model = train_model(df)

    latest = df.iloc[-1]
    features = latest[['sma5','sma10','sma30','rsi','macd','volume']].values.reshape(1,-1)

    prediction = model.predict(features)[0]
    confidence = np.max(model.predict_proba(features)) * 100

    price = latest['close']

    if prediction == 1 and confidence > 60:
        signal = "BUY"
        stop_loss = price * 0.99
        target = price * 1.02
    elif prediction == 0 and confidence > 60:
        signal = "SELL"
        stop_loss = price * 1.01
        target = price * 0.98
    else:
        signal = "WAIT"
        stop_loss = "-"
        target = "-"

    message = f"""
📊 BTC/USDT SIGNAL

💰 Price: {price}

📈 Signal: {signal}
📊 Confidence: {round(confidence,2)}%

🛑 Stop Loss: {stop_loss}
🎯 Target: {target}
"""

    send_message(message)

# ====== AUTO LOOP ======
def auto_trade():
    while True:
        try:
            generate_signal()
            time.sleep(900)  # 15 minutes
        except:
            time.sleep(60)

# ====== TELEGRAM WEBHOOK ======
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    data = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json()

    if data["result"]:
        message = data["result"][-1]["message"]["text"]

        if message == "1":
            generate_signal()

    return "ok"

# ====== START ======
if __name__ == "__main__":
    threading.Thread(target=auto_trade).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
