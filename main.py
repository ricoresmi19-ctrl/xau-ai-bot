import requests
import pandas as pd
import numpy as np
import ta
import time
from flask import Flask, render_template_string
from threading import Thread

API_KEY = "MASUKKAN_API_KEY_KAMU"

app = Flask(__name__)

latest_signal = {
    "direction": "WAIT",
    "price": 0,
    "confidence": 0,
    "time": "-"
}

# =========================
# GET DATA 1 MIN (HEMAT API)
# =========================
def get_data():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1min&outputsize=500&apikey={API_KEY}"
    r = requests.get(url).json()

    if "values" not in r:
        print("API Error:", r)
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)

    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    return df

# =========================
# STRATEGY SCALPING PRO
# =========================
def strategy(df):
    df["ema9"] = ta.trend.ema_indicator(df["close"], 9)
    df["ema21"] = ta.trend.ema_indicator(df["close"], 21)
    df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
    df["rsi"] = ta.momentum.rsi(df["close"], 14)

    df.dropna(inplace=True)

    last = df.iloc[-1]

    score = 0

    # Trend filter
    if last["ema9"] > last["ema21"]:
        score += 1
    if last["ema21"] > last["ema50"]:
        score += 1
    if last["rsi"] > 55:
        score += 1

    if score >= 3:
        return "BUY", last["close"], score/3

    score = 0

    if last["ema9"] < last["ema21"]:
        score += 1
    if last["ema21"] < last["ema50"]:
        score += 1
    if last["rsi"] < 45:
        score += 1

    if score >= 3:
        return "SELL", last["close"], score/3

    return "WAIT", last["close"], 0

# =========================
# BACKGROUND LOOP
# =========================
def bot_loop():
    global latest_signal

    while True:
        df1 = get_data()
        if df1 is None:
            time.sleep(60)
            continue

        direction, price, confidence = strategy(df1)

        latest_signal = {
            "direction": direction,
            "price": round(price,2),
            "confidence": round(confidence*100,2),
            "time": pd.Timestamp.now()
        }

        print(latest_signal)

        time.sleep(65)  # aman API

# =========================
# WEB MONITOR
# =========================
@app.route("/")
def home():
    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="20">
        <title>XAUUSD Scalping Pro</title>
    </head>
    <body style="font-family:Arial;text-align:center;background:#111;color:white;">
        <h1>🔥 XAUUSD SCALPING PRO 🔥</h1>
        <h2>Signal: {{direction}}</h2>
        <h3>Price: {{price}}</h3>
        <h3>Confidence: {{confidence}}%</h3>
        <p>Last Update: {{time}}</p>
        <hr>
        <p>Modal 200rb | Risk 3% per trade</p>
    </body>
    </html>
    """
    return render_template_string(html, **latest_signal)

# =========================
# START THREAD
# =========================
if __name__ == "__main__":
    t = Thread(target=bot_loop)
    t.start()
    app.run(host="0.0.0.0", port=8080)

