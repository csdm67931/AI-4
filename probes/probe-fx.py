# -*- coding: utf-8 -*-
"""
資料源探測：外匯（題 6 用）
路徑 (a)：Yahoo chart 端點（TWD=X／JPY=X／KRW=X），抓近一年日資料。
路徑 (b)：台灣銀行牌告匯率歷史 CSV（rate.bot.com.tw）。

實測結果：路徑 (b) 目前會被台灣銀行網站的機器人偵測攔下（回傳一個
"Challenge Validation" 頁面、內含 JS/加密挑戰，需要瀏覽器執行 JS 才能過關）。
依規範不嘗試繞過機器人偵測／CAPTCHA，因此本腳本只示範偵測到的攔截情形，
不做進一步嘗試；正式資料改用路徑 (a) Yahoo chart 端點。

用法：python -X utf8 probe-fx.py
"""
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}
TIMEOUT = 20

OUT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = OUT_DIR / "output"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = {
    "TWD=X": "USD/TWD",
    "JPY=X": "USD/JPY",
    "KRW=X": "USD/KRW",
}


def fetch_with_retry(url, params):
    last_err = None
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[重試 {attempt+1}] {url} -> {e}")
            time.sleep(1)
    raise RuntimeError(f"連續失敗：{url} / {last_err}")


def probe_yahoo(symbol: str, name: str):
    print(f"\n=== (a) Yahoo chart: {symbol} ({name}) ===")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    resp = fetch_with_retry(url, {"range": "1y", "interval": "1d"})
    data = resp.json()
    result = data["chart"]["result"][0]
    meta = result["meta"]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    print(f"代號有效：是。longName={meta.get('longName')}, 時區={meta.get('exchangeTimezoneName')} "
          f"(gmtoffset={meta.get('gmtoffset')})")
    print(f"筆數：{len(ts)}")
    first_dt = datetime.fromtimestamp(ts[0], tz=timezone.utc)
    last_dt = datetime.fromtimestamp(ts[-1], tz=timezone.utc)
    print(f"日期範圍（UTC）：{first_dt.date()} ~ {last_dt.date()}")
    print("欄位：", list(quote.keys()), "（只有 open/high/low/close，無獨立買入/賣出價——這是中價/收盤價，非牌告買賣價）")

    rows = []
    for i, t in enumerate(ts):
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        rows.append(
            {
                "date_utc": dt.strftime("%Y-%m-%d"),
                "timestamp": t,
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": quote["close"][i],
            }
        )

    sample_path = BACKUP_DIR / f"sample-fx-yahoo-{symbol.replace('=', '')}.csv"
    with open(sample_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date_utc", "timestamp", "open", "high", "low", "close"])
        writer.writeheader()
        for row in rows[:20]:
            writer.writerow(row)
    print(f"樣本已存：{sample_path}")

    backup_path = BACKUP_DIR / f"fx-yahoo-{symbol.replace('=', '')}-{datetime.now():%Y-%m-%d}.csv"
    with open(backup_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date_utc", "timestamp", "open", "high", "low", "close"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"備援已存：{backup_path}（近一年，{len(rows)} 筆）")


def probe_bot_history():
    print("\n=== (b) 台灣銀行牌告匯率歷史 CSV ===")
    url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    resp = fetch_with_retry(url, {})
    text = resp.text
    if "Challenge Validation" in text or "sec-container" in text:
        print("狀態：被機器人偵測攔下（回傳 JS/加密挑戰頁面，非真實牌告內容）。")
        print("依規範不嘗試繞過 CAPTCHA／機器人偵測，此路徑判定為 ❌ 失敗。")
        print(f"回應片段：{text[:200]}")
    else:
        print(f"回應長度：{len(text)}，未偵測到攔截頁，可能可用（需人工再確認歷史下載連結）。")


def main():
    for symbol, name in SYMBOLS.items():
        probe_yahoo(symbol, name)
    probe_bot_history()


if __name__ == "__main__":
    main()
