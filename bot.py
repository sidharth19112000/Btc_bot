import ccxt
import pandas as pd
import ta
import requests
from flask import Flask, request

# ==============================
# TELEGRAM
# ==============================
TOKEN = "8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8"
CHAT_ID = "6094849602"

def send_message(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ==============================
# EXCHANGE
# ==============================
exchange = ccxt.okx()
symbol = 'BTC/USDT'

# ==============================
# GET DATA FUNCTION
# ==============================
def get_data(timeframe):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma30'] = df['close'].rolling(30).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()

    return df

# ==============================
# 15 MIN TREND
# ==============================
def trend_15m():
    df = get_data('15m')
    last = df.iloc[-1]

    if last['ma5'] > last['ma10'] > last['ma30']:
        return "BUY"
    elif last['ma5'] < last['ma10'] < last['ma30']:
        return "SELL"
    else:
        return "SIDEWAYS"

# ==============================
# 1 MIN ENTRY
# ==============================
def entry_1m():
    df = get_data('1m')
    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = round(last['close'], 2)

    buy = prev['ma5'] < prev['ma10'] and last['ma5'] > last['ma10'] and last['rsi'] > 50
    sell = prev['ma5'] > prev['ma10'] and last['ma5'] < last['ma10'] and last['rsi'] < 50

    if buy:
        return "BUY", price
    elif sell:
        return "SELL", price
    else:
        return "WAIT", price

# ==============================
# FINAL ANALYSIS
# ==============================
def analyze():
    trend = trend_15m()
    entry, price = entry_1m()

    # Decision logic
    if trend == "BUY" and entry == "BUY":
        decision = "STRONG BUY"
        confidence = 80
        sl = round(price * 0.99, 2)
        tp = round(price * 1.02, 2)

    elif trend == "SELL" and entry == "SELL":
        decision = "STRONG SELL"
        confidence = 80
        sl = round(price * 1.01, 2)
        tp = round(price * 0.98, 2)

    else:
        decision = "WAIT"
        confidence = 40
        sl = "-"
        tp = "-"

    return trend, entry, decision, confidence, price, sl, tp

# ==============================
# FLASK WEBHOOK
# ==============================
app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json

    try:
        text = data['message']['text']

        if text == "1":
            trend, entry, decision, conf, price, sl, tp = analyze()

            msg = f"""
📊 BTC/USDT MULTI-TF ANALYSIS

💰 Price: {price}

📈 15m Trend: {trend}
⚡ 1m Entry: {entry}

🎯 Final: {decision}
📊 Confidence: {conf}%

🛑 Stop Loss: {sl}
🎯 Target: {tp}

⚠️ {'Take Trade' if decision != 'WAIT' else 'Avoid Trade'}
"""
            send_message(msg)

    except Exception as e:
        print("Error:", e)

    return "ok"

# ==============================
# START
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
