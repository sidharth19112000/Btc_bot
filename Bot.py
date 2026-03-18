import ccxt
import pandas as pd
import ta
import requests
import time

symbol = 'BTC/USDT'
timeframe = '15m'

TELEGRAM_TOKEN = '8791048311:AAFLQRG0W7F- 6SNNcUmaBRwKMHfz190osa8'
CHAT_ID = '6094849602'

exchange = ccxt.coinbase()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": msg})

def get_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    return df

def apply_indicators(df):
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma30'] = df['close'].rolling(30).mean()
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['volume_avg'] = df['volume'].rolling(10).mean()
    return df

def check_buy(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    trend = last['ma5'] > last['ma10'] > last['ma30']
    crossover = prev['ma5'] <= prev['ma10'] and last['ma5'] > last['ma10']
    rsi_ok = last['rsi'] > 50
    volume_ok = last['volume'] > last['volume_avg']

    return trend and crossover and rsi_ok and volume_ok

print("Bot started...")

while True:
    try:
        df = get_data()
        df = apply_indicators(df)

        if check_buy(df):
            price = df.iloc[-1]['close']
            send_telegram(f"🚀 BUY BTC at {price}")
            print("BUY:", price)

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
