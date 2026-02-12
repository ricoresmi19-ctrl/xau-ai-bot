import os
import requests
import pandas as pd
import numpy as np
import time
import ta
from sklearn.ensemble import RandomForestClassifier
from telegram import Bot

# ========================
# ENV VARIABLES (Railway)
# ========================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=TOKEN)
bot.send_message(chat_id=CHAT_ID, text="✅ Bot berhasil online")


# ========================
# GET DATA XAUUSD
# ========================
def get_data():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=200&apikey={API_KEY}"
    
    try:
        r = requests.get(url).json()
        
        if "values" not in r:
            print("❌ Data tidak tersedia:", r)
            return None
        
        df = pd.DataFrame(r['values'])
        df = df.iloc[::-1]

        for col in ['open','high','low','close']:
            df[col] = df[col].astype(float)

        return df

    except Exception as e:
        print("ERROR GET DATA:", e)
        return None


# ========================
# AI SIGNAL
# ========================
def run_bot():
    df = get_data()
    if df is None:
        return

    df['rsi'] = ta.momentum.rsi(df['close'], 14)
    df['ema'] = ta.trend.ema_indicator(df['close'], 20)
    df = df.dropna()

    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)

    X = df[['rsi','ema']][:-1]
    y = df['target'][:-1]

    model = RandomForestClassifier()
    model.fit(X,y)

    last = df.iloc[-1]
    prob = model.predict_proba([[last['rsi'], last['ema']]])[0]

    buy_prob = prob[1]
    sell_prob = prob[0]
    price = last['close']

    print(f"Harga: {price} | BuyProb: {buy_prob} | SellProb: {sell_prob}")

    if buy_prob > 0.7:
        msg = f"🤖 BUY XAUUSD\nEntry: {price}\nConfidence: {round(buy_prob*100,2)}%"
        bot.send_message(chat_id=CHAT_ID,text=msg)
        print("Signal BUY terkirim")

    elif sell_prob > 0.7:
        msg = f"🤖 SELL XAUUSD\nEntry: {price}\nConfidence: {round(sell_prob*100,2)}%"
        bot.send_message(chat_id=CHAT_ID,text=msg)
        print("Signal SELL terkirim")


# ========================
# LOOP
# ========================
if __name__ == "__main__":
    print("Bot AI XAUUSD aktif...")
    while True:
        run_bot()
        time.sleep(60)
