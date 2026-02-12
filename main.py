import os
import requests
import pandas as pd
import numpy as np
import time
import ta
from sklearn.ensemble import RandomForestClassifier
from telegram import Bot

TOKEN = os.getenv("8292809405:AAF3ZJWbK7oOuxDlS1R5K0R04NbwT-dHgpQ")
CHAT_ID = os.getenv("8535165886")

bot = Bot(token=TOKEN)

def get_data():
    url = "https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=200&apikey=demo"
    r = requests.get(url).json()
    if "values" not in r:
        return None
    df = pd.DataFrame(r['values'])
    df = df.iloc[::-1]
    for col in ['open','high','low','close']:
        df[col] = df[col].astype(float)
    return df

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

    if buy_prob > 0.7:
        msg = f"🤖 BUY AI\nEntry: {price}\nConfidence: {round(buy_prob*100,2)}%"
        bot.send_message(chat_id=CHAT_ID,text=msg)

    elif sell_prob > 0.7:
        msg = f"🤖 SELL AI\nEntry: {price}\nConfidence: {round(sell_prob*100,2)}%"
        bot.send_message(chat_id=CHAT_ID,text=msg)

while True:
    run_bot()
    time.sleep(300)
