"""rewind-trader API — time-travel backtest endpoints."""
import os, time, random
from datetime import datetime, timedelta
import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from ..data.mock_data import generate_price_history, get_mock_snapshot

app = FastAPI(title="RewindTrader", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
async def health():
    return {"status": "ok", "project": "rewind-trader"}

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

    # Strategy: simple MA crossover
    strategy_return = investment
    position = 0.0
    in_pos = False
    strategy_trades = 0
    strategy_equity = [investment]

    for i in range(20, len(prices)):
        ma_short = np.mean(prices[max(0,i-7):i])
        ma_long = np.mean(prices[max(0,i-25):i])
        current = prices[i]

        if strategy == "ma_cross":
            if ma_short > ma_long and not in_pos:
                position = strategy_return / current
                strategy_return = 0
                in_pos = True
                strategy_trades += 1
            elif ma_short < ma_long and in_pos:
                strategy_return = position * current
                position = 0
                in_pos = False
                strategy_trades += 1
        elif strategy == "dca":
            # Weekly DCA
            if i % 7 == 0:
                bnb = (investment / len(prices)) / current
                position += bnb
                strategy_trades += 1
            if i == len(prices) - 1:
                strategy_return = position * current

        mtm = strategy_return + (position * current if in_pos or strategy == "dca" else 0)
        strategy_equity.append(mtm)

    if strategy != "hold":
        final_val = strategy_return + (position * prices[-1] if in_pos or strategy == "dca" else 0)
        strategy_return_pct = (final_val - investment) / investment * 100
    else:
        strategy_return_pct = total_return

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
        "strategy_return_pct": round(strategy_return_pct, 2),
        "strategy_trades": strategy_trades,
        "equity_curve": strategy_equity[-200:] if len(strategy_equity) > 200 else strategy_equity,
        "prices": prices,
        "timestamp": int(time.time()),
    }
