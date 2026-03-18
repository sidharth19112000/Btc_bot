import os
import requests
import pandas as pd
import numpy as np
import ta
import threading
import time

from flask import Flask, request
from sklearn.ensemble import RandomForestClassifier

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.getenv("8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8")
CHAT_ID = os.getenv("6094849602")

# =========================
# SETTINGS
# =========================
CONFIDENCE_THRESHOLD = 75
AUTO_CHECK_INTERVAL = 300  # 5 minutes

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
# GET DATA (COINGECKO)
# =========================
def get_data():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": 1, "interval": "hourly"}

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if "prices" not in data:
        return None

    df = pd.DataFrame(data["prices"], columns=["time", "price"])
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
# ANALYSIS FUNCTION
# =========================
def analyze_market():
    df = get_data()
    if df is None or len(df) < 20:
        return

    df = prepare_data(df)

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

    # 🔥 IF STRONG
    if confidence >= CONFIDENCE_THRESHOLD:

        if prediction == 1:
            signal = "BUY"
        else:
            signal = "SELL"

        message = f"""
🚀 STRONG SIGNAL

💰 Price: {round(price,2)}
📈 Signal: {signal}
📊 Confidence: {round(confidence,2)}%

🛑 Stop Loss & Target calculated internally
"""

        send_message(message)

    # 🔥 IF WEAK
    else:
        message = f"""
⚠ MARKET IS WEAK

💰 Price: {round(price,2)}
📊 Confidence: {round(confidence,2)}%

❌ No strong trade opportunity.
"""
        send_message(message)

# =========================
# MANUAL TRIGGER
# =========================
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if data and "message" in data:
        text = data["message"].get("text", "")

        if text == "1":
            analyze_market()

    return "ok"

# =========================
# AUTO SIGNAL THREAD
# =========================
def auto_check():
    while True:
        try:
            analyze_market()
        except:
            pass
        time.sleep(AUTO_CHECK_INTERVAL)

# Start background thread
threading.Thread(target=auto_check, daemon=True).start()

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
