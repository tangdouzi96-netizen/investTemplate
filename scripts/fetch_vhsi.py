# -*- coding: utf-8 -*-
"""
港股恒指波幅指数(VHSI)抓取脚本 V1.1 (V5.5.14版)
优先抓取当前可用的 Yahoo Finance 符号，作为港股情绪主锚。
"""
import yfinance as yf
from datetime import datetime
import json
import os

VHSI_SYMBOLS = ["^HSIL", "^VHSI"]  # Yahoo Finance 代码，^VHSI 已失效时回退到 ^HSIL
OUTPUT_FILE = "08-决策追踪/vhsi_monitoring.json"


def fetch_vhsi():
    hist = None
    symbol_used = None
    last_error = None

    for symbol in VHSI_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            candidate = ticker.history(period="5d")
            if not candidate.empty:
                hist = candidate
                symbol_used = symbol
                break
        except Exception as exc:  # pragma: no cover - 网络异常或符号失效
            last_error = exc

    if hist is None or hist.empty:
        raise ValueError(f"Failed to fetch VHSI data: {last_error}")

    latest = hist.iloc[-1]
    vhsi = round(float(latest["Close"]), 2)

    data = {
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "vhsi_close": vhsi,
        "level": get_vhsi_level(vhsi),
        "source_symbol": symbol_used,
        "timestamp": datetime.now().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"VHSI: {data['vhsi_close']} ({data['level']})")
    return data


def get_vhsi_level(vhsi):
    if vhsi < 22:
        return "平静期"
    if vhsi < 27:
        return "谨慎期"
    if vhsi < 32:
        return "恐慌期"
    if vhsi < 40:
        return "高度恐慌期"
    return "极端恐慌期"


if __name__ == "__main__":
    fetch_vhsi()
