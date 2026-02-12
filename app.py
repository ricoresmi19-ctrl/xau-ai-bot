import requests
import pandas as pd
import ta
import time
from flask import Flask, render_template_string
from threading import Thread

API_KEY = "150558b14aac4c49a8c1f4511c38c3e3

app = Flask(__name__)

latest_signal = {
    "direction": "WAIT",
    "score": 0,
    "price": 0,
    "tp": 0,
    "sl": 0,
    "confidence": 0,
    "time": "-"
}

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

def ai_strategy(df):

    df["ema9"] = ta.trend.ema_indicator(df["close"], 9)
    df["ema21"] = ta.trend.ema_indicator(df["close"], 21)
    df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
    df["ema200"] = ta.trend.ema_indicator(df["close"], 200)
    df["rsi"] = ta.momentum.rsi(df["close"], 14)
    df["macd"] = ta.trend.macd_diff(df["close"])
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], 14)
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], 14)

    df.dropna(inplace=True)
    last = df.iloc[-1]

    score = 0

    if last["close"] > last["ema200"]:
        score += 2
    else:
        score -= 2

    if last["ema50"] > last["ema200"]:
        score += 1
    else:
        score -= 1

    if last["rsi"] > 55:
        score += 1
    if last["rsi"] < 45:
        score -= 1

    if last["macd"] > 0:
        score += 1
    else:
        score -= 1

    if last["adx"] > 20:
        score += 1

    direction = "WAIT"

    if score >= 5:
        direction = "BUY"
    elif score <= -5:
        direction = "SELL"

    price = last["close"]
    atr = last["atr"]

    if direction == "BUY":
        tp = price + (atr * 1.5)
        sl = price - (atr * 1.0)
    elif direction == "SELL":
        tp = price - (atr * 1.5)
        sl = price + (atr * 1.0)
    else:
        tp = 0
        sl = 0

    confidence = min(abs(score) * 10, 90)

    return direction, score, price, tp, sl, confidence

def bot_loop():
    global latest_signal

    while True:
        df = get_data()
        if df is None:
            time.sleep(60)
            continue

        direction, score, price, tp, sl, confidence = ai_strategy(df)

        latest_signal = {
            "direction": direction,
            "score": score,
            "price": round(price,2),
            "tp": round(tp,2),
            "sl": round(sl,2),
            "confidence": confidence,
            "time": pd.Timestamp.now()
        }

        print(latest_signal)
        time.sleep(65)

@app.route("/")
def home():
    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="20">
        <title>XAU AI</title>
    </head>
    <body style="font-family:Arial;text-align:center;background:#111;color:white;">
        <h1>XAUUSD AI SCALPING</h1>
        <h2>Signal: {{direction}}</h2>
        <h3>Score: {{score}}</h3>
        <h3>Entry: {{price}}</h3>
        <h3>TP: {{tp}}</h3>
        <h3>SL: {{sl}}</h3>
        <h3>Confidence: {{confidence}}%</h3>
        <p>Last Update: {{time}}</p>
    </body>
    </html>
    """
    return render_template_string(html, **latest_signal)

if __name__ == "__main__":
    t = Thread(target=bot_loop)
    t.start()
    app.run(host="0.0.0.0", port=8080)
