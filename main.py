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


# ================= BOT ENGINE =================
def run_bot():
    global last_signal_time
    global monitor_data

    while True:
        df1 = get_tf("1min")
        df5 = get_tf("5min")
        df15 = get_tf("15min")

        if df1 is None or df5 is None or df15 is None:
            time.sleep(60)
            continue

        current_candle = df5.iloc[-1]["datetime"]

        if current_candle == last_signal_time:
            time.sleep(30)
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

        signal = "NONE"

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

        if trend_buy and momentum_buy and entry_buy:
            signal = "BUY"

        elif trend_sell and momentum_sell and entry_sell:
            signal = "SELL"

        sl_distance = atr * 0.8
        tp_distance = atr * 1.6

        if signal == "BUY":
            sl = round(price - sl_distance, 2)
            tp = round(price + tp_distance, 2)

        elif signal == "SELL":
            sl = round(price + sl_distance, 2)
            tp = round(price - tp_distance, 2)

        else:
            sl = "-"
            tp = "-"

        if signal != "NONE":
            last_signal_time = current_candle

        monitor_data = {
            "price": round(price,2),
            "signal": signal,
            "sl": sl,
            "tp": tp,
            "trend": "BUY" if trend_buy else "SELL",
            "rsi": round(last5["rsi"],2)
        }

        time.sleep(30)


# ================= WEB DASHBOARD =================
@app.route("/")
def dashboard():
    html = f"""
    <html>
    <head>
        <title>XAUUSD Scalping PRO</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{
                background: #111;
                color: white;
                font-family: Arial;
                text-align: center;
            }}
            .box {{
                margin: 20px auto;
                padding: 20px;
                width: 300px;
                background: #222;
                border-radius: 10px;
            }}
            .buy {{ color: #00ff88; }}
            .sell {{ color: #ff4444; }}
        </style>
    </head>
    <body>
        <h1>🔥 XAUUSD SCALPING PRO</h1>
        <div class="box">
            <h2>Price: {monitor_data['price']}</h2>
            <h2 class="{monitor_data['signal'].lower()}">
                Signal: {monitor_data['signal']}
            </h2>
            <p>SL: {monitor_data['sl']}</p>
            <p>TP: {monitor_data['tp']}</p>
            <p>Trend 15M: {monitor_data['trend']}</p>
            <p>RSI 5M: {monitor_data['rsi']}</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


# ================= START =================
if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
