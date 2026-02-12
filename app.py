import requests
import pandas as pd
import ta
import time
import os

API_KEY = "4295156bcbd24bffa6163ec156b5dce1"

def get_data(interval):
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&outputsize=300&apikey={4295156bcbd24bffa6163ec156b5dce1}"
    r = requests.get(url).json()

    if "values" not in r:
        print("API Error:", r)
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)

    return df

def analyze(df):
    df["ema9"] = ta.trend.ema_indicator(df["close"], 9)
    df["ema21"] = ta.trend.ema_indicator(df["close"], 21)
    df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
    df["rsi"] = ta.momentum.rsi(df["close"], 14)
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], 14)
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], 14)

    df.dropna(inplace=True)
    return df.iloc[-1]

def signal_logic(tf1, tf5):

    confidence = 0

    # Trend confirmation
    if tf1["ema9"] > tf1["ema21"] > tf1["ema50"]:
        confidence += 25
    if tf5["ema9"] > tf5["ema21"] > tf5["ema50"]:
        confidence += 25

    if tf1["rsi"] > 55:
        confidence += 15
    if tf5["rsi"] > 55:
        confidence += 15

    if tf1["adx"] > 20:
        confidence += 10
    if tf5["adx"] > 20:
        confidence += 10

    price = tf1["close"]
    atr = tf1["atr"]

    if confidence >= 70:
        tp = price + atr * 1.8
        sl = price - atr
        return "BUY", price, tp, sl, confidence

    # SELL condition
    confidence = 0

    if tf1["ema9"] < tf1["ema21"] < tf1["ema50"]:
        confidence += 25
    if tf5["ema9"] < tf5["ema21"] < tf5["ema50"]:
        confidence += 25

    if tf1["rsi"] < 45:
        confidence += 15
    if tf5["rsi"] < 45:
        confidence += 15

    if tf1["adx"] > 20:
        confidence += 10
    if tf5["adx"] > 20:
        confidence += 10

    if confidence >= 70:
        tp = price - atr * 1.8
        sl = price + atr
        return "SELL", price, tp, sl, confidence

    return "WAIT", price, 0, 0, confidence


last_signal = ""

while True:

    os.system("clear")

    df1 = get_data("1min")
    df5 = get_data("5min")

    if df1 is None or df5 is None:
        time.sleep(60)
        continue

    tf1 = analyze(df1)
    tf5 = analyze(df5)

    signal, price, tp, sl, conf = signal_logic(tf1, tf5)

    print("===== XAUUSD PRO SCALPING BOT =====")
    print("Harga :", round(price,2))
    print("Signal:", signal)
    print("Confidence:", conf,"%")

    if signal != "WAIT" and signal != last_signal:

        print("\n🔥 SIGNAL KUAT 🔥")
        print("Entry :", round(price,2))
        print("TP    :", round(tp,2))
        print("SL    :", round(sl,2))
        print("\a")

        last_signal = signal

    time.sleep(60)
