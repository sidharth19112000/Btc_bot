import ccxt
import pandas as pd
import ta
import time
import requests
from flask import Flask
import threading

# ==============================
# 🔑 YOUR TELEGRAM DETAILS
# ==============================
TOKEN = "8791048311:AAFLQRG0W7F-6SNNcUmaBRwKMHfz19Oosa8"
CHAT_ID = "6094849602"

# ==============================
# 📡 TELEGRAM FUNCTION
# ==============================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# ==============================
# 📊 GET MARKET DATA (OKX)
# ==============================
exchange = ccxt.okx()

def get_data():
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

    # Indicators
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma30'] = df['close'].rolling(30).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['vol_avg'] = df['volume'].rolling(20).mean()

    return df

# ==============================
# 🤖 TRADING LOGIC
# ==============================
def run_bot():
    print("Bot started...")

    # ✅ TEST MESSAGE
    send_telegram("✅ Bot is live and working!")

    last_signal = ""

    while True:
        try:
            df = get_data()
            last = df.iloc[-1]

            price = last['close']

            # BUY CONDITIONS
            buy_condition = (
                last['ma5'] > last['ma10'] > last['ma30'] and
                last['rsi'] > 45 and
                last['volume'] > last['vol_avg']
            )

            # SELL CONDITIONS
            sell_condition = (
                last['ma5'] < last['ma10'] < last['ma30'] and
                last['rsi'] < 55 and
                last['volume'] > last['vol_avg']
            )

            # SIGNALS
            if buy_condition and last_signal != "BUY":
                msg = f"🟢 BUY SIGNAL\nPrice: {price}"
                print(msg)
                send_telegram(msg)
                last_signal = "BUY"

            elif sell_condition and last_signal != "SELL":
                msg = f"🔴 SELL SIGNAL\nPrice: {price}"
                print(msg)
                send_telegram(msg)
                last_signal = "SELL"

            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

# ==============================
# 🌐 FLASK SERVER (RENDER FIX)
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 BTC Bot Running Successfully!"

# ==============================
# ▶️ START BOT + SERVER
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
