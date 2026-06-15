"""
Binance public API client — no API key required, accessible globally.
Used as fallback when CMC API is unreachable.
"""
import time
from typing import Optional

import requests

from .cmc_client import MarketSnapshot, PricePoint

BINANCE_BASE = "https://api.binance.com"


def get_bnb_price() -> float:
    """Get current BNB/USDT price from Binance."""
    resp = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price", params={"symbol": "BNBUSDT"}, timeout=6)
    resp.raise_for_status()
    return float(resp.json()["price"])


def get_bnb_24h() -> dict:
    """Get 24h ticker stats."""
    resp = requests.get(f"{BINANCE_BASE}/api/v3/ticker/24hr", params={"symbol": "BNBUSDT"}, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    return {
        "price": float(data["lastPrice"]),
        "change_pct": float(data["priceChangePercent"]),
        "volume": float(data["quoteVolume"]),
        "high": float(data["highPrice"]),
        "low": float(data["lowPrice"]),
    }


def get_bnb_klines(interval: str = "1d", limit: int = 90) -> list[PricePoint]:
    """Fetch historical klines (candlesticks)."""
    resp = requests.get(
        f"{BINANCE_BASE}/api/v3/klines",
        params={"symbol": "BNBUSDT", "interval": interval, "limit": limit},
        timeout=8,
    )
    resp.raise_for_status()
    points = []
    for k in resp.json():
        close = float(k[4])
        volume = float(k[7])  # quote asset volume
        ts = k[6] // 1000  # close time in ms → seconds
        points.append(PricePoint(
            timestamp=int(ts),
            price=close,
            volume_24h=volume,
            market_cap=0,  # Binance doesn't provide this
        ))
    # Compute 24h changes
    for i in range(1, len(points)):
        if points[i - 1].price > 0:
            points[i].percent_change_24h = (
                (points[i].price - points[i - 1].price) / points[i - 1].price * 100
            )
    return points


def get_binance_snapshot(symbol: str = "BNB") -> MarketSnapshot:
    """Build a full MarketSnapshot from Binance data."""
    ticker = get_bnb_24h()
    price_history = get_bnb_klines("1d", 90)

    # Estimate Fear & Greed from recent price action
    if len(price_history) >= 14:
        recent = [p.price for p in price_history[-14:]]
        trend = (recent[-1] - recent[0]) / recent[0] * 100
        # Map trend to 0-100 scale: -10% → 20, 0% → 50, +10% → 80
        fg = int(50 + trend * 3)
        fg = max(5, min(95, fg))
    else:
        fg = 50

    snap = MarketSnapshot(
        symbol=symbol,
        current_price=ticker["price"],
        price_history=price_history,
        volume_24h=ticker["volume"],
        market_cap=0,
        market_cap_dominance=0,
        fear_greed_index=fg,
        percent_change_24h=ticker["change_pct"],
    )
    return snap
