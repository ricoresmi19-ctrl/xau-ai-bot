import os
import requests
import pandas as pd
import numpy as np
import time
import ta
from sklearn.ensemble import RandomForestClassifier
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)

last_candle_time = None

def get_data():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=200&apikey={API_KEY}"
    r = requests.get(url).json()

    if "values" not in r:
        print("Data gagal:", r)
        return None

    df = pd.DataFrame(r['values'])
    df = df.iloc[::-1]

    for col in ['open','high','low','close']:
        df[col] = df[col].astype(float)

    return df


def run_bot():
    global last_candle_time

    df = get_data()
    if df is None:
        return

    current_candle_time = df.iloc[-1]['datetime']

    # Anti spam (hanya 1x per candle)
    if current_candle_time == last_candle_time:
        return

    last_candle_time = current_candle_time

    df['rsi'] = ta.momentum.rsi(df['close'], 14)
    df['ema'] = ta.trend.ema_indicator(df['close'], 20)
    df = df.dropna()

    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)

    X = df[['rsi','ema']][:-1]
    y = df['target'][:-1]

    model = RandomForestClassifier()
    model.fit(X,y)

    last = df.iloc[-1]

    last_data = pd.DataFrame([[last['rsi'], last['ema']]], columns=['rsi','ema'])
    prob = model.predict_proba(last_data)[0]

    buy_prob = prob[1]
    sell_prob = prob[0]
    price = last['close']

    confidence = round(max(buy_prob, sell_prob)*100,2)

    # ===== SIGNAL LOGIC =====
    if buy_prob > 0.6:
        sl = price - 5
        tp = price + 10

        msg = f"""
🚀 AI SIGNAL XAUUSD (5M)

📈 BUY
Entry : {price}
SL    : {round(sl,2)}
TP    : {round(tp,2)}

Confidence : {confidence}%
        """

        bot.send_message(chat_id=CHAT_ID, text=msg)

    elif sell_prob > 0.6:
        sl = price + 5
        tp = price - 10

        msg = f"""
🚀 AI SIGNAL XAUUSD (5M)

📉 SELL
Entry : {price}
SL    : {round(sl,2)}
TP    : {round(tp,2)}

Confidence : {confidence}%
        """

        bot.send_message(chat_id=CHAT_ID, text=msg)

    print("Candle checked:", current_candle_time)


if __name__ == "__main__":
    print("Bot AI PRO aktif...")
    while True:
        run_bot()
        time.sleep(60)
