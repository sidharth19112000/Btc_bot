import os
import ccxt
import pandas as pd
import numpy as np
import tensorflow as tf
import requests
import threading
import time
from flask import Flask, request
from sklearn.preprocessing import MinMaxScaler

# ==============================
# TELEGRAM SETTINGS (Render ENV)
# ==============================

TOKEN = os.environ.get("8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8")
CHAT_ID = os.environ.get("6094849602")

SYMBOL = "BTC/USDT"
TIMEFRAME = "15m"

app = Flask(__name__)

exchange = ccxt.binance()

# ==============================
# CREATE OR LOAD LSTM MODEL
# ==============================

MODEL_PATH = "lstm_model.h5"

def create_model():

    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, input_shape=(50,1)),
        tf.keras.layers.Dense(1)
    ])

    model.compile(optimizer="adam", loss="mse")
    return model

if os.path.exists(MODEL_PATH):
    model = tf.keras.models.load_model(MODEL_PATH)
else:
    model = create_model()

# ==============================
# SEND TELEGRAM MESSAGE
# ==============================

def send_message(text):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

# ==============================
# TRAIN LSTM AUTOMATICALLY
# ==============================

def train_model():

    data = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=1000)
    df = pd.DataFrame(data, columns=["t","o","h","l","c","v"])

    prices = df["c"].values.reshape(-1,1)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(prices)

    X, y = [], []

    for i in range(50, len(scaled)):
        X.append(scaled[i-50:i])
        y.append(scaled[i])

    X, y = np.array(X), np.array(y)

    model.fit(X, y, epochs=5, verbose=0)

    model.save(MODEL_PATH)

# ==============================
# LSTM SIGNAL
# ==============================

def lstm_signal():

    data = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
    df = pd.DataFrame(data, columns=["t","o","h","l","c","v"])

    prices = df["c"].values.reshape(-1,1)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(prices)

    X = np.array(scaled[-50:]).reshape(1,50,1)

    prediction = model.predict(X, verbose=0)[0][0]
    current = scaled[-1][0]

    confidence = abs(prediction - current) * 100

    if prediction > current:
        return "BUY", confidence
    else:
        return "SELL", confidence

# ==============================
# RISK PERCENTAGE
# ==============================

def calculate_risk(df):

    df["atr"] = df["c"].rolling(14).std()

    volatility = df["atr"].iloc[-1] / df["c"].iloc[-1]

    if volatility < 0.005:
        return 80
    elif volatility < 0.01:
        return 60
    else:
        return 40

# ==============================
# AUTO SIGNAL LOOP
# ==============================

def auto_loop():

    while True:

        try:

            signal, confidence = lstm_signal()
            price = exchange.fetch_ticker(SYMBOL)["last"]

            data = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=50)
            df = pd.DataFrame(data, columns=["t","o","h","l","c","v"])

            risk = calculate_risk(df)

            if confidence > 0.5:

                send_message(f"""
🤖 AUTO LSTM TRADE

Price: {price}
Signal: {signal}
Confidence: {round(confidence,2)}%
Risk Level: {risk}%
""")

        except Exception as e:
            print(e)

        time.sleep(900)

# ==============================
# WEBHOOK (MANUAL CHECK)
# ==============================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    if "message" in data:

        text = data["message"].get("text")

        if text == "1":

            price = exchange.fetch_ticker(SYMBOL)["last"]
            signal, confidence = lstm_signal()

            send_message(f"""
📊 MANUAL CHECK

Price: {price}
Signal: {signal}
Confidence: {round(confidence,2)}%
""")

    return "ok"

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    # Train if model does not exist
    if not os.path.exists(MODEL_PATH):
        train_model()

    threading.Thread(target=auto_loop).start()

    app.run(host="0.0.0.0", port=10000)
