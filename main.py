import os
import requests
import pandas as pd
import time
import ta
from flask import Flask, render_template_string
from threading import Thread

API_KEY = os.getenv("API_KEY")

app = Flask(__name__)

last_signal_time = None
monitor_data = {
    "price": "-",
    "signal": "NONE",
    "sl": "-",
    "tp": "-",
    "trend": "-",
    "rsi": "-"
}

# ================= GET DATA =================
def get_tf(interval):
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&outputsize=200&apikey={API_KEY}"
    r = requests.get(url).json()

    if "values" not in r:
        print("API Error:", r)
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    return df


# ================= BOT LOOP =================
def bot_loop():
    global last_signal_time
    global monitor_data

    while True:
        try:
            df1 = get_tf("1min")
            df5 = get_tf("5min")
            df15 = get_tf("15min")

            if df1 is None or df5 is None or df15 is None:
                time.sleep(30)
                continue

            current_candle = df5.iloc[-1]["datetime"]

            if current_candle == last_signal_time:
                time.sleep(20)
                continue

            for df in [df1, df5, df15]:
                df["ema_fast"] = ta.trend.ema_indicator(df["close"], 9)
                df["ema_slow"] = ta.trend.ema_indicator(df["close"], 21)
                df["rsi"] = ta.momentum.rsi(df["close"], 14)
                df["macd"] = ta.trend.macd_diff(df["close"])
                df["atr"] = ta.volatility.average_true_range(
                    df["high"], df["low"], df["close"], 14
                )
                df.dropna(inplace=True)

            last1 = df1.iloc[-1]
            last5 = df5.iloc[-1]
            last15 = df15.iloc[-1]

            price = last1["close"]
            atr = last5["atr"]

            trend_buy = last15["ema_fast"] > last15["ema_slow"]
            trend_sell = last15["ema_fast"] < last15["ema_slow"]

            momentum_buy = (
                last5["ema_fast"] > last5["ema_slow"]
                and last5["rsi"] > 55
                and last5["macd"] > 0
            )

            momentum_sell = (
                last5["ema_fast"] < last5["ema_slow"]
                and last5["rsi"] < 45
                and last5["macd"] < 0
            )

            entry_buy = last1["ema_fast"] > last1["ema_slow"]
            entry_sell = last1["ema_fast"] < last1["ema_slow"]

            signal = "NONE"

            if trend_buy and momentum_buy and entry_buy:
                signal = "BUY"
            elif trend_sell and momentum_sell and entry_sell:
                signal = "SELL"

            sl_distance = atr * 0.8
            tp_distance = atr * 1.6

            if signal == "BUY":
                sl = round(price - sl_distance, 2)
                tp = round(price + tp_distance, 2)
                last_signal_time = current_candle
            elif signal == "SELL":
                sl = round(price + sl_distance, 2)
                tp = round(price - tp_distance, 2)
                last_signal_time = current_candle
            else:
                sl = "-"
                tp = "-"

            monitor_data.update({
                "price": round(price,2),
                "signal": signal,
                "sl": sl,
                "tp": tp,
                "trend": "BUY" if trend_buy else "SELL",
                "rsi": round(last5["rsi"],2)
            })

        except Exception as e:
            print("ERROR LOOP:", e)

        time.sleep(20)


# ================= DASHBOARD =================
@app.route("/")
def dashboard():
    return render_template_string(f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="10">
    <style>
    body {{ background:#111; color:white; text-align:center; font-family:Arial }}
    .buy {{ color:#00ff88 }}
    .sell {{ color:#ff4444 }}
    </style>
    </head>
    <body>
    <h1>🔥 XAUUSD SCALPING PRO</h1>
    <h2>Price: {monitor_data['price']}</h2>
    <h2 class="{monitor_data['signal'].lower()}">Signal: {monitor_data['signal']}</h2>
    <p>SL: {monitor_data['sl']}</p>
    <p>TP: {monitor_data['tp']}</p>
    <p>Trend 15M: {monitor_data['trend']}</p>
    <p>RSI 5M: {monitor_data['rsi']}</p>
    </body>
    </html>
    """)


# ================= START THREAD =================
thread = Thread(target=bot_loop)
thread.daemon = True
thread.start()
