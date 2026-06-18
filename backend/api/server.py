"""rewind-trader API — time-travel backtest endpoints."""
import os, time, random
from datetime import datetime, timedelta
import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from ..data.mock_data import generate_price_history, get_mock_snapshot

app = FastAPI(title="RewindTrader", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Indicator helpers ──

def _rsi(prices: list, period: int = 14) -> float:
    if len(prices) < period + 1: return 50
    diffs = np.diff(prices[-(period+1):])
    gains = np.maximum(diffs, 0)
    losses = np.abs(np.minimum(diffs, 0))
    avg_gain = np.mean(gains) or 1e-9
    avg_loss = np.mean(losses) or 1e-9
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

def _macd(prices: list) -> tuple:
    """Return (macd_line, signal_line, histogram)"""
    if len(prices) < 35: return 0, 0, 0
    closes = np.array(prices)
    fast, slow, sig = 12, 26, 9
    # Fast EMA
    ema_fast = float(np.mean(closes[:fast]))
    alpha_f = 2.0 / (fast + 1)
    for p in closes[fast:]:
        ema_fast = alpha_f * p + (1 - alpha_f) * ema_fast
    # Slow EMA
    ema_slow = float(np.mean(closes[:slow]))
    alpha_s = 2.0 / (slow + 1)
    for p in closes[slow:]:
        ema_slow = alpha_s * p + (1 - alpha_s) * ema_slow
    # MACD line
    macd_line = ema_fast - ema_slow
    # Signal line: compute MACD history first
    ef = float(np.mean(closes[:fast]))
    es = float(np.mean(closes[:slow]))
    macd_hist = []
    for i in range(max(fast, slow), len(closes)):
        ef = alpha_f * closes[i] + (1 - alpha_f) * ef
        es = alpha_s * closes[i] + (1 - alpha_s) * es
        macd_hist.append(ef - es)
    if len(macd_hist) >= sig:
        signal = float(np.mean(macd_hist[:sig]))
        alpha_sig = 2.0 / (sig + 1)
        for v in macd_hist[sig:]:
            signal = alpha_sig * v + (1 - alpha_sig) * signal
    else:
        signal = macd_line
    return float(macd_line), float(signal), float(macd_line - signal)

def _bollinger(prices: list, period: int = 20) -> tuple:
    """Return (upper, mid, lower)"""
    if len(prices) < period: return 0, 0, 0
    w = np.array(prices[-period:])
    mid = float(np.mean(w))
    std = float(np.std(w))
    return mid + 2*std, mid, mid - 2*std

# ── Strategy descriptions ──

STRATEGY_META = {
    "hold":       {"name": "Buy & Hold",    "icon": "💎", "desc": "Buy BNB once and never sell — benchmark strategy."},
    "ma_cross":   {"name": "MA Crossover",  "icon": "📈", "desc": "Buy when 7-day MA crosses above 25-day MA, sell on reverse."},
    "dca":        {"name": "DCA (Weekly)",   "icon": "📅", "desc": "Invest equal amounts every week regardless of price."},
    "rsi":        {"name": "RSI Signal",     "icon": "📊", "desc": "Buy when RSI<35 (oversold), sell when RSI>70 (overbought)."},
    "bollinger":  {"name": "Bollinger Bands","icon": "🎯", "desc": "Buy at lower band (bounce), sell at upper band (pullback)."},
    "macd":       {"name": "MACD Cross",     "icon": "⚡", "desc": "Buy on bullish MACD crossover, sell on bearish crossover."},
}

@app.get("/api/health")
async def health():
    return {"status": "ok", "project": "rewind-trader"}

@app.get("/api/strategies")
async def list_strategies():
    return [{"id": k, **v} for k, v in STRATEGY_META.items()]

@app.get("/api/rewind")
async def rewind(
    symbol: str = "BNB",
    days_ago: int = 180,
    investment: float = 1000,
    strategy: str = "hold",
):
    """Simulate: what if I invested $X, Y days ago, using strategy Z?"""
    snap = get_mock_snapshot(symbol, count=days_ago + 30)
    prices = [p.price for p in snap.price_history]

    if len(prices) < 30:
        return {"error": "Not enough data"}

    # Slice to exactly days_ago
    prices = prices[-days_ago:] if len(prices) > days_ago else prices
    start_price = prices[0]
    end_price = prices[-1]
    bnb_bought = investment / start_price
    final_value = bnb_bought * end_price
    total_return = (final_value - investment) / investment * 100

    # Strategy simulation
    cash = investment
    position = 0.0
    in_pos = False
    strategy_trades = 0
    strategy_equity = []

    # Hold: buy immediately at prices[0]
    if strategy == "hold":
        position = investment / prices[0]
        cash = 0
        in_pos = True
        strategy_trades = 1
        for i in range(20):
            strategy_equity.append(position * prices[i])

    if not strategy_equity:
        strategy_equity = [investment]

    for i in range(20, len(prices)):
        ma_short = np.mean(prices[max(0,i-7):i])
        ma_long = np.mean(prices[max(0,i-25):i])
        current = prices[i]

        if strategy == "ma_cross":
            if ma_short > ma_long and not in_pos:
                position = cash / current; cash = 0; in_pos = True; strategy_trades += 1
            elif ma_short < ma_long and in_pos:
                cash = position * current; position = 0; in_pos = False; strategy_trades += 1

        elif strategy == "dca":
            total_windows = max(1, (len(prices) - 20) // 7)
            amount_per_buy = investment / total_windows
            if i % 7 == 0 and cash >= amount_per_buy:
                position += amount_per_buy / current
                cash -= amount_per_buy
                strategy_trades += 1

        elif strategy == "rsi":
            window = prices[max(0,i-20):i+1]
            rsi_val = _rsi(window)
            if rsi_val < 35 and not in_pos:
                position = cash / current; cash = 0; in_pos = True; strategy_trades += 1
            elif rsi_val > 70 and in_pos:
                cash = position * current; position = 0; in_pos = False; strategy_trades += 1

        elif strategy == "bollinger":
            bb_upper, bb_mid, bb_lower = _bollinger(prices[:i+1])
            if bb_lower > 0 and current <= bb_lower * 1.02 and not in_pos:
                position = cash / current; cash = 0; in_pos = True; strategy_trades += 1
            elif bb_upper > 0 and current >= bb_upper * 0.98 and in_pos:
                cash = position * current; position = 0; in_pos = False; strategy_trades += 1

        elif strategy == "macd":
            macd_l, macd_s, macd_h = _macd(prices[:i+1])
            if macd_h > 0 and not in_pos:
                position = cash / current; cash = 0; in_pos = True; strategy_trades += 1
            elif macd_h < 0 and in_pos:
                cash = position * current; position = 0; in_pos = False; strategy_trades += 1

        mtm = cash + (position * current if in_pos or strategy in ("dca", "hold") else 0)
        strategy_equity.append(mtm)

    final_val = cash + (position * prices[-1] if in_pos or strategy in ("dca", "hold") else 0)
    strategy_return_pct = (final_val - investment) / investment * 100

    start_date = datetime.now() - timedelta(days=days_ago)

    return {
        "symbol": symbol,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "days_ago": days_ago,
        "investment": investment,
        "start_price": round(start_price, 2),
        "end_price": round(end_price, 2),
        "bnb_bought": round(bnb_bought, 6),
        "hold_return_pct": round(total_return, 2),
        "hold_final_value": round(final_value, 2),
        "strategy": strategy,
        "strategy_info": STRATEGY_META.get(strategy, STRATEGY_META["hold"]),
        "strategy_return_pct": round(strategy_return_pct, 2),
        "strategy_trades": strategy_trades,
        "equity_curve": strategy_equity[-200:] if len(strategy_equity) > 200 else strategy_equity,
        "prices": prices,
        "timestamp": int(time.time()),
    }
