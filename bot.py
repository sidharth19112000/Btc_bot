import os
import requests
import pandas as pd
import numpy as np
import ta

from flask import Flask, request
from sklearn.ensemble import RandomForestClassifier

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.getenv("8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8")
CHAT_ID = os.getenv("6094849602")

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

# =========================
# TELEGRAM SEND
# =========================
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

# =========================
# GET BTC DATA (COINGECKO)
# =========================
def get_data():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": 1, "interval": "hourly"}

    response = requests.get(url, params=params)
    data = response.json()

    prices = data["prices"]

    df = pd.DataFrame(prices, columns=["time", "price"])
    df["close"] = df["price"]

    return df

# =========================
# PREPARE DATA
# =========================
def prepare_data(df):
    df["sma5"] = ta.trend.sma_indicator(df["close"], 5)
    df["sma10"] = ta.trend.sma_indicator(df["close"], 10)
    df["rsi"] = ta.momentum.rsi(df["close"], 14)

    df = df.dropna()

    df["target"] = np.where(df["close"].shift(-1) > df["close"], 1, 0)

    return df

# =========================
# GENERATE SIGNAL
# =========================
def generate_signal():
    df = get_data()
    df = prepare_data(df)

    if len(df) < 20:
        return

    model = RandomForestClassifier(n_estimators=100)

    features = ["sma5", "sma10", "rsi"]

    X = df[features]
    y = df["target"]

    model.fit(X, y)

    latest = df.iloc[-1]
    input_data = latest[features].values.reshape(1, -1)

    prediction = model.predict(input_data)[0]
    confidence = np.max(model.predict_proba(input_data)) * 100
    price = latest["close"]

    # 🔥 Strong filter
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

💰 Price: {round(price,2)}
📈 Signal: {signal}
📊 Confidence: {round(confidence,2)}%

🛑 Stop Loss: {round(stop_loss,2)}
🎯 Target: {round(target,2)}
"""

    send_message(message)

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
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
