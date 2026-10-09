# -*- coding: utf-8 -*-
"""
AI CRYPTO MARKET ANALYZER
Binance or MEXC + Technical Analysis + OpenRouter Multi-AI

WHAT THIS VERSION ADDS
----------------------
1. Binance market analysis (kept from the original version).
2. MEXC market analysis.
3. Select exactly one exchange: BINANCE or MEXC at startup.
4. The same coin list can be analyzed on both exchanges.
5. MEXC public market-data API is used, so an MEXC API key is NOT
   required for this analysis-only program.
6. This program does NOT place real trades.

IMPORTANT
---------
- This is a market-analysis tool, not financial advice.
- BUY / SELL / WAIT are analytical signals, not guarantees.
- Never put your exchange Secret Key in this file or GitHub.
- If you later want private MEXC/Binance account data or automated
  trading, API authentication must be added separately and securely.
"""

# ============================================================
# 1. INSTALL LIBRARIES
# ============================================================

import sys
import subprocess
import importlib.util

packages = {
    "requests": "requests",
    "pandas": "pandas",
    "numpy": "numpy",
    "pydantic": "pydantic",
}

for module, package in packages.items():
    if importlib.util.find_spec(module) is None:
        print(f"Installing {package}...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            package
        ])

# ============================================================
# 2. IMPORTS
# ============================================================

import requests
import pandas as pd
import numpy as np
import time
import json
import re

from getpass import getpass
from pydantic import BaseModel

# ============================================================
# 3. SETTINGS
# ============================================================

BINANCE_BASE_URL = "https://data-api.binance.vision"
MEXC_BASE_URL = "https://api.mexc.com"

# OpenRouter API
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# You can add/remove model IDs here.
# The program also lets you enter any OpenRouter model ID manually.
# Free OpenRouter models used by default.
# These do not require purchased OpenRouter credits, although free
# endpoints are rate-limited.
OPENROUTER_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3-ultra-550b-a55b-20260604:free",
    "inclusionai/ling-3.0-flash:free",
]

# Automatic fallback order used when a selected model fails.
FREE_FALLBACK_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3-ultra-550b-a55b-20260604:free",
    "inclusionai/ling-3.0-flash:free",
]

CANDLE_LIMIT = 300
TIMEFRAMES = ["15m", "1h", "4h"]

# MEXC uses different interval names from Binance.
MEXC_INTERVALS = {
    # These are the SPOT API v3 interval names.
    # Min15/Min60/Hour4 are MEXC FUTURES-style names and should not be used here.
    "15m": "15m",
    "1h": "60m",
    "4h": "4h",
}

# ============================================================
# 4. AI RESPONSE STRUCTURE
# ============================================================

class CoinDecision(BaseModel):
    exchange: str
    symbol: str
    signal: str
    confidence: int
    trend: str
    momentum: str
    reasons: list[str]
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    risk: str


class AIAnalysis(BaseModel):
    decisions: list[CoinDecision]

# ============================================================
# 5. OPENROUTER API KEY INPUT
# ============================================================

print("\n")
print("=" * 70)
print("                      OPENROUTER API")
print("=" * 70)

print("\nEnter your OpenRouter API key.")
print("Your API key will NOT be displayed while typing.")
print("The program does NOT save the key.\n")

OPENROUTER_API_KEY = getpass(
    "Enter OpenRouter API key: "
).strip()

if not OPENROUTER_API_KEY:
    raise ValueError("No OpenRouter API key was entered.")

print("\nOpenRouter API key accepted.")

# ============================================================
# 5A. AI MODEL SELECTION
# ============================================================

print("\n")
print("=" * 70)
print("                         AI MODEL SELECTION")
print("=" * 70)

print("\nFree OpenRouter models available by default:")
for i, model_name in enumerate(OPENROUTER_MODELS, 1):
    print(f"{i} = {model_name}")

print("\nYou can:")
print("  - Enter one number to use one AI model.")
print("  - Enter several numbers separated by commas to run multiple AI models.")
print("  - Enter 'custom' to type any OpenRouter model ID.")
print("  - Enter 'all' to run all free default models.")
print("  - Enter 'auto' to use the free router with automatic fallback.")

model_choice = input(
    "\nSelect AI model(s) [Enter = auto]: "
).strip()

SELECTED_AI_MODELS = []

if not model_choice or model_choice.lower() == "auto":
    SELECTED_AI_MODELS = ["openrouter/free"]

elif model_choice.lower() == "all":
    SELECTED_AI_MODELS = OPENROUTER_MODELS.copy()

elif model_choice.lower() == "custom":
    custom_model = input(
        "Enter OpenRouter model ID (example: openai/gpt-5): "
    ).strip()

    if not custom_model:
        raise ValueError("No OpenRouter model ID was entered.")

    SELECTED_AI_MODELS = [custom_model]

else:
    try:
        indexes = [
            int(x.strip())
            for x in model_choice.split(",")
            if x.strip()
        ]

        for index in indexes:
            if index < 1 or index > len(OPENROUTER_MODELS):
                raise ValueError

            model_name = OPENROUTER_MODELS[index - 1]

            if model_name not in SELECTED_AI_MODELS:
                SELECTED_AI_MODELS.append(model_name)

    except ValueError:
        raise ValueError(
            "Invalid AI model selection. Use numbers such as 1 or 1,2,3, "
            "'auto', 'custom', or 'all'."
        )

if not SELECTED_AI_MODELS:
    raise ValueError("No AI model was selected.")

print("\nSelected AI model(s):")
for model_name in SELECTED_AI_MODELS:
    print("  •", model_name)

# ============================================================
# 6. EXCHANGE SELECTION
# ============================================================

print("\n")
print("=" * 70)
print("                       EXCHANGE SELECTION")
print("=" * 70)

print("""
Choose where you want to analyze the coins:

1 = Binance
2 = MEXC
""")

exchange_choice = input("Enter 1 or 2: ").strip()

if exchange_choice == "1":
    EXCHANGES = ["BINANCE"]
elif exchange_choice == "2":
    EXCHANGES = ["MEXC"]
else:
    raise ValueError("Invalid exchange choice. Please enter 1 or 2.")

print(f"\nSelected exchange: {EXCHANGES[0]}")

# 7. COIN INPUT
# ============================================================

print("\n")
print("=" * 70)
print("                         COIN SELECTION")
print("=" * 70)

print("\nEnter the coins you want to analyze.")
print("Example:")
print("BTC, ETH, SOL, XRP, BNB")
print("\nYou can also write:")
print("BTCUSDT, ETHUSDT, SOLUSDT\n")

coin_input = input(
    "Enter coins: "
).strip()

if not coin_input:
    raise ValueError("No coins were entered.")

symbols = []

for coin in coin_input.split(","):
    coin = coin.strip().upper()

    if not coin:
        continue

    if not coin.endswith("USDT"):
        coin = coin + "USDT"

    if coin not in symbols:
        symbols.append(coin)

if not symbols:
    raise ValueError("No valid coins were entered.")

print("\nSelected coins:")
for symbol in symbols:
    print("  •", symbol)

# ============================================================
# 8. SYMBOL NORMALIZATION
# ============================================================

# We intentionally do NOT call exchangeInfo before requesting candles.
# This keeps the data path simple and avoids rejecting valid MEXC symbols
# because of exchangeInfo/status differences. The candle endpoint is the
# source of truth: if it returns data, the symbol is usable.

# 9. GET BINANCE CANDLES
# ============================================================

def get_binance_klines(symbol, interval, limit=CANDLE_LIMIT):
    url = f"{BINANCE_BASE_URL}/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            return None

        columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ]

        df = pd.DataFrame(data, columns=columns)

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df["open_time"] = pd.to_datetime(
            df["open_time"],
            unit="ms"
        )

        df["close_time"] = pd.to_datetime(
            df["close_time"],
            unit="ms"
        )

        return df

    except Exception as e:
        print(
            f"Binance error {symbol} {interval}: {e}"
        )
        return None

# ============================================================
# 10. GET MEXC CANDLES
# ============================================================

def get_mexc_klines(symbol, interval, limit=CANDLE_LIMIT):
    """Fetch MEXC SPOT candles directly from /api/v3/klines."""
    mexc_interval = MEXC_INTERVALS.get(interval)
    if not mexc_interval:
        print(f"Unsupported MEXC interval: {interval}")
        return None

    url = f"{MEXC_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": mexc_interval, "limit": limit}

    try:
        response = requests.get(
            url,
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Crypto-Analyzer/2.0",
            },
            timeout=30,
        )

        if not response.ok:
            print(f"MEXC HTTP {response.status_code} | {response.url}")
            print(f"MEXC response: {response.text[:800]}")
            return None

        data = response.json()
        if not isinstance(data, list):
            print(f"MEXC unexpected response: {str(data)[:800]}")
            return None

        rows = [row[:8] for row in data if isinstance(row, list) and len(row) >= 8]
        if not rows:
            print(f"MEXC returned no candles for {symbol} {interval}.")
            return None

        df = pd.DataFrame(rows, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume"
        ])

        for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", errors="coerce")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"]).reset_index(drop=True)

        if len(df) < 220:
            print(f"MEXC returned only {len(df)} usable candles for {symbol} {interval}; need at least 220.")
            return None

        return df

    except requests.RequestException as e:
        print(f"MEXC network error {symbol} {interval}: {e}")
        return None
    except Exception as e:
        print(f"MEXC parse error {symbol} {interval}: {e}")
        return None

# 11. GENERIC CANDLE FUNCTION
# ============================================================

def get_klines(exchange, symbol, interval, limit=CANDLE_LIMIT):
    if exchange == "BINANCE":
        return get_binance_klines(
            symbol,
            interval,
            limit
        )

    if exchange == "MEXC":
        return get_mexc_klines(
            symbol,
            interval,
            limit
        )

    return None

# ============================================================
# 11B. LIVE TICKER PRICE (instant, candle-independent)
# ============================================================
# The "price" used everywhere so far was the close of the LAST candle
# in the 4h kline list. That candle is usually still forming and does
# track the live price closely, but it still depends on how each
# exchange times candle boundaries, and it costs an extra 300-candle
# download just to read one number. To make the displayed price
# unmistakably "right now", it is fetched separately from each
# exchange's lightweight ticker endpoint, which returns nothing but
# the single latest traded price - the same number the exchange's own
# website shows.

import datetime as _dt


def get_binance_ticker_price(symbol):
    url = f"{BINANCE_BASE_URL}/api/v3/ticker/price"

    try:
        response = requests.get(
            url,
            params={"symbol": symbol},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return float(data["price"])

    except Exception as e:
        print(f"Binance ticker error {symbol}: {e}")
        return None


def get_mexc_ticker_price(symbol):
    url = f"{MEXC_BASE_URL}/api/v3/ticker/price"

    try:
        response = requests.get(
            url,
            params={"symbol": symbol},
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Crypto-Analyzer/2.0",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return float(data["price"])

    except Exception as e:
        print(f"MEXC ticker error {symbol}: {e}")
        return None


def get_live_price(exchange, symbol):
    """
    Returns (price, fetched_at_utc_string) using each exchange's
    instant ticker endpoint - not a candle close. Returns
    (None, None) if the request fails, so callers can fall back to
    the candle-based price instead of crashing.
    """
    if exchange == "BINANCE":
        price = get_binance_ticker_price(symbol)
    elif exchange == "MEXC":
        price = get_mexc_ticker_price(symbol)
    else:
        price = None

    if price is None:
        return None, None

    fetched_at = _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    return price, fetched_at

# ============================================================
# 12. TECHNICAL INDICATORS
# ============================================================

def calculate_indicators(df):
    df = df.copy()

    # --------------------------------------------------------
    # EMA 20
    # --------------------------------------------------------

    df["EMA20"] = (
        df["close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    # --------------------------------------------------------
    # EMA 50
    # --------------------------------------------------------

    df["EMA50"] = (
        df["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    # --------------------------------------------------------
    # EMA 200
    # --------------------------------------------------------

    df["EMA200"] = (
        df["close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    # --------------------------------------------------------
    # RSI 14
    # --------------------------------------------------------

    delta = df["close"].diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = (
        gain
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    avg_loss = (
        loss
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    df["RSI"] = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    df["RSI"] = df["RSI"].fillna(50)

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = (
        df["close"]
        .ewm(
            span=12,
            adjust=False
        )
        .mean()
    )

    ema26 = (
        df["close"]
        .ewm(
            span=26,
            adjust=False
        )
        .mean()
    )

    df["MACD"] = ema12 - ema26

    df["MACD_signal"] = (
        df["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    df["MACD_hist"] = (
        df["MACD"] -
        df["MACD_signal"]
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    previous_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]

    tr2 = (
        df["high"] -
        previous_close
    ).abs()

    tr3 = (
        df["low"] -
        previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = (
        true_range
        .rolling(14)
        .mean()
    )

    # --------------------------------------------------------
    # Average Volume
    # --------------------------------------------------------

    df["Volume_MA20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    return df

# ============================================================
# 13. TECHNICAL SCORE
# ============================================================

def calculate_score(df):
    latest = df.iloc[-1]

    score = 0
    reasons = []

    # --------------------------------------------------------
    # EMA TREND
    # --------------------------------------------------------

    if (
        latest["close"]
        >
        latest["EMA20"]
        >
        latest["EMA50"]
        >
        latest["EMA200"]
    ):
        score += 3
        reasons.append(
            "Strong bullish EMA alignment"
        )

    elif (
        latest["close"]
        <
        latest["EMA20"]
        <
        latest["EMA50"]
        <
        latest["EMA200"]
    ):
        score -= 3
        reasons.append(
            "Strong bearish EMA alignment"
        )

    elif latest["close"] > latest["EMA200"]:
        score += 1
        reasons.append(
            "Price above EMA200"
        )

    elif latest["close"] < latest["EMA200"]:
        score -= 1
        reasons.append(
            "Price below EMA200"
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi = latest["RSI"]

    if 50 < rsi < 70:
        score += 1
        reasons.append(
            "Bullish RSI momentum"
        )

    elif 30 < rsi < 50:
        score -= 1
        reasons.append(
            "Bearish RSI momentum"
        )

    elif rsi >= 70:
        reasons.append(
            "RSI is overbought"
        )

    elif rsi <= 30:
        reasons.append(
            "RSI is oversold"
        )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        latest["MACD"]
        >
        latest["MACD_signal"]
    ):
        score += 1
        reasons.append(
            "MACD bullish"
        )

    else:
        score -= 1
        reasons.append(
            "MACD bearish"
        )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    if (
        latest["volume"]
        >
        latest["Volume_MA20"]
    ):
        if score > 0:
            score += 1
            reasons.append(
                "Volume supports bullish movement"
            )

        elif score < 0:
            score -= 1
            reasons.append(
                "Volume supports bearish movement"
            )

    return score, reasons

# ============================================================
# 14. ANALYZE ONE TIMEFRAME
# ============================================================

def analyze_timeframe(
    exchange,
    symbol,
    timeframe
):
    df = get_klines(
        exchange,
        symbol,
        timeframe,
        CANDLE_LIMIT
    )

    if df is None:
        return None

    df = calculate_indicators(df)

    df = df.dropna(
        subset=[
            "EMA20",
            "EMA50",
            "EMA200",
            "RSI",
            "MACD",
            "MACD_signal",
            "ATR",
            "Volume_MA20"
        ]
    )

    if len(df) < 10:
        return None

    score, reasons = calculate_score(df)

    latest = df.iloc[-1]

    return {
        "timeframe": timeframe,
        "price": float(latest["close"]),
        "EMA20": float(latest["EMA20"]),
        "EMA50": float(latest["EMA50"]),
        "EMA200": float(latest["EMA200"]),
        "RSI": float(latest["RSI"]),
        "MACD": float(latest["MACD"]),
        "MACD_signal": float(latest["MACD_signal"]),
        "ATR": float(latest["ATR"]),
        "volume": float(latest["volume"]),
        "volume_ma20": float(latest["Volume_MA20"]),
        "score": int(score),
        "reasons": reasons
    }

# ============================================================
# 15. ANALYZE ONE COIN
# ============================================================

def analyze_coin(exchange, symbol):
    print("\n")
    print("-" * 70)
    print(
        f"Analyzing {exchange} | {symbol}"
    )
    print("-" * 70)

    results = {}

    for timeframe in TIMEFRAMES:
        print(
            f"Downloading {timeframe}..."
        )

        result = analyze_timeframe(
            exchange,
            symbol,
            timeframe
        )

        if result:
            results[timeframe] = result

            print(
                f"✓ {timeframe} | "
                f"Score: {result['score']} | "
                f"RSI: {result['RSI']:.2f}"
            )

        else:
            print(
                f"✗ {timeframe} failed"
            )

    if len(results) != 3:
        print(
            f"Skipping {exchange} {symbol}."
        )
        return None

    # --------------------------------------------------------
    # WEIGHTED SCORE
    # --------------------------------------------------------

    score_15m = results["15m"]["score"]
    score_1h = results["1h"]["score"]
    score_4h = results["4h"]["score"]

    final_score = (
        score_15m * 0.20
        +
        score_1h * 0.30
        +
        score_4h * 0.50
    )

    # --------------------------------------------------------
    # TECHNICAL SIGNAL
    # --------------------------------------------------------

    if final_score >= 4:
        technical_signal = "BUY"

    elif final_score <= -4:
        technical_signal = "SELL"

    else:
        technical_signal = "WAIT"

    # --------------------------------------------------------
    # ENTRY / SL / TP
    # --------------------------------------------------------

    # Prefer the instant ticker price (what the exchange's own site
    # shows right now) over the 4h candle close. Only fall back to the
    # candle close if the ticker request itself fails.
    live_price, price_fetched_at = get_live_price(exchange, symbol)

    if live_price is not None:
        current_price = live_price
        print(
            f"Live {exchange} price for {symbol}: {current_price} "
            f"(fetched {price_fetched_at})"
        )
    else:
        current_price = results["4h"]["price"]
        price_fetched_at = None
        print(
            f"Ticker fetch failed for {exchange} {symbol}; "
            f"falling back to last 4h candle close: {current_price}"
        )

    atr = results["4h"]["ATR"]

    if technical_signal == "BUY":
        entry = current_price

        stop_loss = (
            entry -
            (1.5 * atr)
        )

        take_profit = (
            entry +
            (3.0 * atr)
        )

    elif technical_signal == "SELL":
        entry = current_price

        stop_loss = (
            entry +
            (1.5 * atr)
        )

        take_profit = (
            entry -
            (3.0 * atr)
        )

    else:
        entry = current_price
        stop_loss = None
        take_profit = None

    return {
        "exchange": exchange,
        "symbol": symbol,
        "technical_signal": technical_signal,
        "final_score": round(
            final_score,
            2
        ),
        "price": current_price,
        "price_fetched_at": price_fetched_at,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "score_15m": score_15m,
        "score_1h": score_1h,
        "score_4h": score_4h,
        "rsi_15m": results["15m"]["RSI"],
        "rsi_1h": results["1h"]["RSI"],
        "rsi_4h": results["4h"]["RSI"],
        "atr_4h": atr,
        "reasons_15m": results["15m"]["reasons"],
        "reasons_1h": results["1h"]["reasons"],
        "reasons_4h": results["4h"]["reasons"]
    }

# ============================================================
# 16. MARKET ANALYSIS
# ============================================================

print("\n")
print("=" * 100)
print(f"                 STARTING {EXCHANGES[0]} MARKET ANALYSIS")
print("=" * 100)

all_results = []

for exchange in EXCHANGES:
    for symbol in symbols:
        try:
            result = analyze_coin(exchange, symbol)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"\n{exchange} | {symbol} analysis error: {e}")

# 18. TECHNICAL RESULTS
# ============================================================

print("\n")
print("=" * 120)
print("                       TECHNICAL SIGNALS")
print("=" * 120)

if not all_results:
    print("No market data was successfully analyzed.")
    sys.exit(1)

results_df = pd.DataFrame(all_results)

# ------------------------------------------------------------
# LIVE PRICE LOOKUP (real exchange data, not AI-generated)
# ------------------------------------------------------------
# The AI model is only asked to judge signal/trend/reasoning.
# Free/small OpenRouter models are not reliable at echoing back
# exact numbers, and can quietly round, drift, or hallucinate a
# "plausible" price (e.g. an old/round BTC figure) instead of
# using the real price that was given to them in the prompt.
# To guarantee the displayed price is always the real, live price
# fetched from Binance/MEXC, every AI decision's entry/stop_loss/
# take_profit is overwritten below using this lookup, keyed by
# (exchange, symbol), right after the AI response is parsed.
technical_lookup = {
    (r["exchange"], r["symbol"]): r
    for r in all_results
}

technical_display = results_df[[
    "exchange", "symbol", "technical_signal", "final_score", "price",
    "price_fetched_at", "entry", "stop_loss", "take_profit", "rsi_15m",
    "rsi_1h", "rsi_4h", "score_15m", "score_1h", "score_4h"
]].copy()

print(technical_display.to_string(index=False))

# 19. PREPARE AI DATA
# ============================================================

def prepare_ai_data(df):
    data = []

    for _, row in df.iterrows():
        data.append({
            "exchange": row["exchange"],
            "symbol": row["symbol"],
            "technical_signal":
                row["technical_signal"],
            "final_score":
                row["final_score"],
            "current_price":
                round(
                    float(row["price"]),
                    8
                ),
            "entry":
                (
                    None
                    if pd.isna(row["entry"])
                    else round(
                        float(row["entry"]),
                        8
                    )
                ),
            "stop_loss":
                (
                    None
                    if pd.isna(row["stop_loss"])
                    else round(
                        float(row["stop_loss"]),
                        8
                    )
                ),
            "take_profit":
                (
                    None
                    if pd.isna(row["take_profit"])
                    else round(
                        float(row["take_profit"]),
                        8
                    )
                ),
            "15m": {
                "score":
                    int(row["score_15m"]),
                "RSI":
                    round(
                        float(row["rsi_15m"]),
                        2
                    ),
                "reasons":
                    row["reasons_15m"]
            },
            "1h": {
                "score":
                    int(row["score_1h"]),
                "RSI":
                    round(
                        float(row["rsi_1h"]),
                        2
                    ),
                "reasons":
                    row["reasons_1h"]
            },
            "4h": {
                "score":
                    int(row["score_4h"]),
                "RSI":
                    round(
                        float(row["rsi_4h"]),
                        2
                    ),
                "ATR":
                    round(
                        float(row["atr_4h"]),
                        8
                    ),
                "reasons":
                    row["reasons_4h"]
            }
        })

    return data

market_data = prepare_ai_data(
    results_df
)

# ============================================================
# 20. OPENROUTER MULTI-AI ANALYSIS
# ============================================================

def extract_json_object(text):
    """
    Extract the first JSON object from an AI response.
    This makes the program work with OpenRouter models that return
    JSON inside a markdown code block or with a small amount of extra text.
    """
    if not text:
        raise ValueError("AI returned an empty response.")

    cleaned = text.strip()

    # Remove common markdown JSON fences.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\\s*```$", "", cleaned).strip()

    # First try the complete response as JSON.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Then locate the first JSON object.
    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character == "{":
            try:
                value, _ = decoder.raw_decode(cleaned[index:])
                return value
            except json.JSONDecodeError:
                continue

    raise ValueError("Could not find valid JSON in the AI response.")


def ask_openrouter(
    market_data,
    model,
    max_retries=3
):
    """
    Ask OpenRouter for the analysis.

    If a selected model fails because of insufficient credits (HTTP 402),
    the caller can automatically try the documented free fallback models.
    The technical-analysis data and prompt remain unchanged.
    """
    prompt = f"""
You are a cryptocurrency market-analysis assistant.

Analyze the technical market data below.

DATA:
{market_data}

Your task is to classify EACH exchange/coin combination as
exactly one of:

BUY
SELL
WAIT

Rules:

1. Use the supplied technical data only.
2. Consider the 15m, 1h and 4h timeframes.
3. Give more importance to the 4h timeframe.
4. If signals conflict significantly, choose WAIT.
5. Do not guarantee profit.
6. Do not invent prices or indicators.
7. This is analysis only.
8. Do not execute trades.
9. Confidence must be between 0 and 100.
10. BUY means bullish setup.
11. SELL means bearish setup.
12. WAIT means there is not enough confirmation.
13. Keep Binance and MEXC results separate.
14. The same coin may have different signals on different exchanges.

For each result provide:

- exchange
- symbol
- signal
- confidence
- trend
- momentum
- key reasons
- entry
- stop loss
- take profit
- risk

The signal MUST be exactly:
BUY, SELL, or WAIT.

Return ONLY valid JSON using this exact structure:

{{
  "decisions": [
    {{
      "exchange": "BINANCE",
      "symbol": "BTCUSDT",
      "signal": "WAIT",
      "confidence": 50,
      "trend": "neutral",
      "momentum": "neutral",
      "reasons": ["reason 1", "reason 2"],
      "entry": 0,
      "stop_loss": null,
      "take_profit": null,
      "risk": "medium"
    }}
  ]
}}
"""

    for attempt in range(1, max_retries + 1):
        try:
            print(
                f"\nOpenRouter AI request | {model} | "
                f"{attempt}/{max_retries}"
            )

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "AI Crypto Market Analyzer",
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a careful cryptocurrency market-analysis "
                            "assistant. Return valid JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.2,
            }

            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if not response.ok:
                error_text = response.text[:2000]
                raise RuntimeError(
                    f"OpenRouter HTTP {response.status_code}: {error_text}"
                )

            response_data = response.json()

            choices = response_data.get("choices", [])
            if not choices:
                raise RuntimeError(
                    f"OpenRouter returned no choices: {response_data}"
                )

            message = choices[0].get("message", {})
            response_text = message.get("content", "")

            if isinstance(response_text, list):
                response_text = "".join(
                    item.get("text", "")
                    for item in response_text
                    if isinstance(item, dict)
                )

            parsed = extract_json_object(response_text)
            ai_data = AIAnalysis.model_validate(parsed)

            return ai_data

        except Exception as e:
            error_text = str(e)

            print("\nOpenRouter error:")
            print(error_text)

            temporary_error = (
                "429" in error_text
                or "500" in error_text
                or "502" in error_text
                or "503" in error_text
                or "504" in error_text
                or "timeout" in error_text.lower()
                or "timed out" in error_text.lower()
            )

            if temporary_error and attempt < max_retries:
                wait_time = 2 ** attempt

                print("Temporary error.")
                print(f"Retrying in {wait_time} seconds...")

                time.sleep(wait_time)
            else:
                return None

    return None


def run_openrouter_with_fallback(market_data, selected_model):
    """
    Try the selected model first.

    On a billing/credit failure (HTTP 402), automatically continue through
    the free OpenRouter fallback list. Other temporary errors are retried
    inside ask_openrouter before moving to the next fallback.
    """
    fallback_chain = [selected_model]

    for fallback_model in FREE_FALLBACK_MODELS:
        if fallback_model not in fallback_chain:
            fallback_chain.append(fallback_model)

    for model_name in fallback_chain:
        print("\n" + "-" * 90)
        print(f"AI MODEL ATTEMPT: {model_name}")

        result = ask_openrouter(
            market_data,
            model_name
        )

        if result:
            print(f"✓ AI analysis completed with {model_name}")
            return model_name, result

        if model_name == selected_model:
            print(
                f"✗ {model_name} did not complete. "
                "Trying the next available free fallback..."
            )
        else:
            print(
                f"✗ Free fallback {model_name} did not complete. "
                "Trying the next fallback..."
            )

    return None, None


def apply_live_prices(ai_analysis, technical_lookup):
    """
    Overwrite entry / stop_loss / take_profit on every AI decision
    with the real, live-computed values from the exchange data.

    The AI is free to choose the SIGNAL, confidence, trend, momentum,
    reasons and risk text, but the actual price numbers it returns are
    never trusted directly - small/free models can drift, round, or
    hallucinate a price instead of repeating the exact one given to
    them. This keeps the displayed price locked to the real, current
    Binance/MEXC price no matter what the AI model outputs.
    """
    for decision in ai_analysis.decisions:
        real = technical_lookup.get(
            (decision.exchange, decision.symbol)
        )

        if real is None:
            # No matching live data for this exchange/symbol; leave as-is.
            continue

        real_entry = real.get("entry")
        real_stop_loss = real.get("stop_loss")
        real_take_profit = real.get("take_profit")

        decision.entry = (
            round(float(real_entry), 8)
            if real_entry is not None and not pd.isna(real_entry)
            else None
        )

        decision.stop_loss = (
            round(float(real_stop_loss), 8)
            if real_stop_loss is not None and not pd.isna(real_stop_loss)
            else None
        )

        decision.take_profit = (
            round(float(real_take_profit), 8)
            if real_take_profit is not None and not pd.isna(real_take_profit)
            else None
        )

    return ai_analysis


# ============================================================
# ============================================================
# 21. RUN OPENROUTER MODELS
# ============================================================

print("\n")
print("=" * 100)
print("                    OPENROUTER MULTI-AI ANALYSIS")
print("=" * 100)

ai_analyses = {}

for model_name in SELECTED_AI_MODELS:
    successful_model, ai_analysis = run_openrouter_with_fallback(
        market_data,
        model_name
    )

    if ai_analysis:
        # Force entry/stop_loss/take_profit back to the real, live
        # exchange price before this result is stored or displayed.
        ai_analysis = apply_live_prices(ai_analysis, technical_lookup)

        # Keep the actual model used as the display key.
        ai_analyses[successful_model] = ai_analysis

if not ai_analyses:
    print("\nNo selected OpenRouter AI model completed the analysis.")
    print("The technical analysis above is still available.")
    print("If you are using a free OpenRouter account, the free endpoints")
    print("may be temporarily rate-limited. Try again later or use 'auto'.")

# ============================================================
# 22. DISPLAY FINAL BUY / SELL / WAIT
# ============================================================

for model_name, ai_analysis in ai_analyses.items():
    print("\n")
    print("=" * 110)
    print(f"              FINAL AI SIGNALS | {model_name}")
    print("=" * 110)

    for decision in ai_analysis.decisions:
        print("\n")
        print("=" * 80)

        print(
            f"EXCHANGE: {decision.exchange}"
        )

        print(
            f"COIN: {decision.symbol}"
        )

        print("=" * 80)

        print(
            f"\n>>> SIGNAL: "
            f"{decision.signal} <<<"
        )

        print(
            f"Confidence: "
            f"{decision.confidence}%"
        )

        print(
            f"Trend: "
            f"{decision.trend}"
        )

        print(
            f"Momentum: "
            f"{decision.momentum}"
        )

        print("\nKey Reasons:")

        for reason in decision.reasons:
            print(
                f"  • {reason}"
            )

        print(
            f"\nEntry (Live Price): "
            f"{decision.entry}"
        )

        _real = technical_lookup.get(
            (decision.exchange, decision.symbol)
        )
        if _real and _real.get("price_fetched_at"):
            print(
                f"Price fetched at: "
                f"{_real['price_fetched_at']}"
            )

        print(
            f"Stop Loss: "
            f"{decision.stop_loss}"
        )

        print(
            f"Take Profit: "
            f"{decision.take_profit}"
        )

        print(
            f"\nRisk: "
            f"{decision.risk}"
        )

# ============================================================
# 23. FINAL SIMPLE TABLE
# ============================================================

for model_name, ai_analysis in ai_analyses.items():
    print("\n")
    print("=" * 110)
    print(f"                 SIMPLE SUMMARY | {model_name}")
    print("=" * 110)

    summary_rows = []

    for decision in ai_analysis.decisions:
        summary_rows.append({
            "EXCHANGE":
                decision.exchange,
            "COIN":
                decision.symbol,
            "SIGNAL":
                decision.signal,
            "CONFIDENCE":
                f"{decision.confidence}%",
            "ENTRY":
                decision.entry,
            "STOP LOSS":
                decision.stop_loss,
            "TAKE PROFIT":
                decision.take_profit
        })

    summary_df = pd.DataFrame(
        summary_rows
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

print("\n")
print("=" * 110)
print("                         SIMPLE SUMMARY")
print("=" * 110)

if ai_analyses:
    last_model_name, last_ai_analysis = next(reversed(ai_analyses.items()))
    print(f"Latest successful AI model: {last_model_name}")
    summary_rows = []

    for decision in last_ai_analysis.decisions:
        summary_rows.append({
            "EXCHANGE":
                decision.exchange,
            "COIN":
                decision.symbol,
            "SIGNAL":
                decision.signal,
            "CONFIDENCE":
                f"{decision.confidence}%",
            "ENTRY":
                decision.entry,
            "STOP LOSS":
                decision.stop_loss,
            "TAKE PROFIT":
                decision.take_profit
        })

    summary_df = pd.DataFrame(
        summary_rows
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

print("\n")
print("=" * 110)

print(
    "Analysis completed."
)

print(
    "BUY / SELL / WAIT are analytical signals, not guarantees."
)

print(
    "This program does NOT place real trades."
)

print(
    "Paper trading/backtesting is recommended before using real money."
)

print("=" * 110)
