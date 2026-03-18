import os
import requests
import ccxt
import pandas as pd
import numpy as np
import ta

from flask import Flask, request
from sklearn.ensemble import RandomForestClassifier

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.getenv("8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz190osa8")
CHAT_ID = os.getenv("6094849602")

# =========================
# EXCHANGE
# =========================
exchange = ccxt.binance()

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

# Root route (for Render health check)
@app.route("/", methods=["GET"])
def home():
    return "Bot Running"

# =========================
# TELEGRAM SEND FUNCTION
# =========================
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

# =========================
# GET DATA
# =========================
def get_data():
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "15m", limit=200)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    return df

# =========================
# PREPARE DATA
# =========================
def prepare_data(df):
    df['sma5'] = ta.trend.sma_indicator(df['close'], 5)
    df['sma10'] = ta.trend.sma_indicator(df['close'], 10)
    df['rsi'] = ta.momentum.rsi(df['close'], 14)
    df['macd'] = ta.trend.macd_diff(df['close'])
    df = df.dropna()

    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    return df

# =========================
# SIGNAL LOGIC
# =========================
def generate_signal():
    df = get_data()
    df = prepare_data(df)

    model = RandomForestClassifier(n_estimators=100)

    features = ['sma5','sma10','rsi','macd']
    X = df[features]
    y = df['target']

    model.fit(X, y)

    latest = df.iloc[-1]
    input_data = latest[features].values.reshape(1, -1)

    prediction = model.predict(input_data)[0]
    confidence = np.max(model.predict_proba(input_data)) * 100
    price = latest['close']

    # Strong signal filter
    if confidence < 75:
        return

    if prediction == 1:
        signal = "BUY"
        stop_loss = price * 0.99
        target = price * 1.02
    else:
        signal = "SELL"
        stop_loss = price * 1.01
        target = price * 0.98

    message = f"""
🚀 STRONG SIGNAL

💰 Price: {price}
📈 Signal: {signal}
📊 Confidence: {round(confidence,2)}%

🛑 Stop Loss: {round(stop_loss,2)}
🎯 Target: {round(target,2)}
"""

    send_message(message)

# =========================
# WEBHOOK ROUTE (STEP 2 FIX)
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if data and "message" in data:
        text = data["message"].get("text", "")

        if text == "1":
            generate_signal()

    return "ok"

# =========================
# START SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
