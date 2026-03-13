from flask import Flask, request
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def send_chart(path, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    with open(path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": f})

# Forex price data — pastdagi API manzilni o‘zgartir
PRICE_API = "https://example-forex-api.com/candles"

# Session filter
def in_session():
    h = datetime.utcnow().hour
    london = 7 <= h <= 16
    newyork = 13 <= h <= 22
    return london or newyork

# News alert
NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
sent_news = set()

def check_news():
    try:
        r = requests.get(NEWS_URL).json()
    except:
        return
    now = datetime.utcnow()
    for n in r:
        if n.get("impact")!="High":
            continue
        title = n.get("title") 
        d = n.get("date")
        t = n.get("time","00:00")
        event = datetime.strptime(f"{d} {t}","%Y-%m-%d %H:%M")
        key_base = f"{title}-{d}-{t}"
        before = event - timedelta(minutes=30)
        after = event + timedelta(minutes=30)
        if before <= now < event:
            if key_base+"-before" not in sent_news:
                send_telegram(f"⚠️ HIGH IMPACT NEWS YAQIN\n{title}\nSavdo qilma!")
                sent_news.add(key_base+"-before")
        if event <= now < after:
            if key_base+"-after" not in sent_news:
                send_telegram(f"✅ NEWS O'TDI\n{title}\nSavdoga ruxsat!")
                sent_news.add(key_base+"after")

# Get candles
def get_candles(symbol, interval="30min"):
    url = f"{PRICE_API}?symbol={symbol}&interval={interval}"
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r["values"])
        for c in ["open","high","low","close"]:
            df[c]=pd.to_numeric(df[c])
        df["datetime"]=pd.to_datetime(df["datetime"])
        return df[::-1]
    except:
        return None

# ATR
def atr(df,n=14):
    tr = pd.concat([
        df["high"]-df["low"],
        (df["high"]-df["close"].shift()).abs(),
        (df["low"]-df["close"].shift()).abs()
    ],axis=1).max(axis=1)
    return tr.rolling(n).mean()

# ZigZag SNR
def find_snr(df):
    peaks = df["high"].rolling(10).max().iloc[-1]
    troughs = df["low"].rolling(10).min().iloc[-1]
    return peaks, troughs

# FVG
def find_fvg(df):
    for i in range(len(df)-1,2,-1):
        c1, c3 = df.iloc[i-2], df.iloc[i]
        if c1["high"]<c3["low"]:
            return ("BUY",c1["high"],c3["low"])
        if c1["low"]>c3["high"]:
            return ("SELL",c3["high"],c1["low"])
    return None

# Liquidity sweep
def liq_sweep(df):
    last=df.iloc[-1]
    prev_high=df["high"][-10:-1].max()
    prev_low=df["low"][-10:-1].min()
    if last["high"]>prev_high:
        return "SELL"
    if last["low"]<prev_low:
        return "BUY"
    return None

# Chart
def draw_chart(df,symbol,entry,sl,tp):
    xs = np.arange(len(df["close"].tail(80)))
    plt.figure(figsize=(8,6))
    plt.plot(xs, df["close"].tail(80), label="Close")
    plt.axhline(entry); plt.axhline(sl); plt.axhline(tp)
    plt.title(symbol)
    plt.savefig("chart.png"); plt.close()

# Main loop
@app.route("/webhook",methods=["POST"])
def webhook():
    try:
        data=request.json
        send_telegram(data.get("alert_message",str(data)))
        return {"status":"ok"},200
    except:
        return {"status":"error"},400

if __name__=="__main__":
    send_telegram("Bot ishga tushdi — Pro Level")
    while True:
        if not in_session():
            time.sleep(60)
            continue
        check_news()
        for sym in ["XAUUSD","XAGUSD"]:
            df=get_candles(sym)
            if df is None: continue
            snr_h,snr_l=find_snr(df)
            fvg=find_fvg(df)
            sweep=liq_sweep(df)
            if not fvg or sweep!=fvg[0]:
                continue
            price=df["close"].iloc[-1]
            side=fvg[0]
            entry=(fvg[1]+fvg[2])/2
            if side=="BUY":
                sl=entry-10; tp=entry+40
            else:
                sl=entry+10; tp=entry-40
            draw_chart(df,sym,entry,sl,tp)
            cap=f"{side} {sym}\nEntry:{entry:.2f}\nSL:{sl:.2f}\nTP:{tp:.2f}"
            send_chart("chart.png",cap)
        time.sleep(60)
