"""
CoinMarketCap API client — fetches real-time market data for all agents.
"""
import os
import time
import hashlib
import hmac
import json
from typing import Optional
from dataclasses import dataclass, field
from functools import lru_cache

import requests
from dotenv import load_dotenv

load_dotenv()

CMC_BASE = "https://pro-api.coinmarketcap.com"


@dataclass
class PricePoint:
    timestamp: int
    price: float
    volume_24h: float
    market_cap: float
    percent_change_1h: float = 0
    percent_change_24h: float = 0


@dataclass
class MarketSnapshot:
    symbol: str
    current_price: float
    price_history: list[PricePoint] = field(default_factory=list)
    volume_24h: float = 0
    market_cap: float = 0
    market_cap_dominance: float = 0
    fear_greed_index: int = 50  # 0-100, 0=extreme fear
    percent_change_1h: float = 0
    percent_change_24h: float = 0
    # Technical indicators (computed later)
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None


class CMCClient:
    """Rate-limited CMC API client with in-memory cache."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CMC_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json",
        })
        self._cache: dict[str, tuple[float, dict]] = {}
        self._cache_ttl = 60  # 1 min for quotes
        self._last_request = 0.0
        self._min_interval = 1.0  # rate limit guard

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def _get(self, endpoint: str, params: dict) -> dict:
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        now = time.time()
        if cache_key in self._cache:
            cached_at, cached_val = self._cache[cache_key]
            if now - cached_at < self._cache_ttl:
                return cached_val

        self._rate_limit()
        resp = self.session.get(f"{CMC_BASE}{endpoint}", params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        self._cache[cache_key] = (now, data)
        return data

    def get_quote(self, symbol: str = "BNB") -> MarketSnapshot:
        """Get latest quote + compute basic technicals."""
        data = self._get("/v1/cryptocurrency/quotes/latest", {"symbol": symbol})
        coin = data["data"][symbol]
        quote = coin["quote"]["USD"]

        snap = MarketSnapshot(
            symbol=symbol,
            current_price=quote["price"],
            volume_24h=quote["volume_24h"],
            market_cap=quote["market_cap"],
            market_cap_dominance=quote.get("market_cap_dominance", 0),
            percent_change_1h=quote.get("percent_change_1h", 0),
            percent_change_24h=quote.get("percent_change_24h", 0),
        )
        return snap

    def get_price_history(self, symbol: str = "BNB", count: int = 90) -> list[PricePoint]:
        """Fetch historical daily OHLCV for backtesting."""
        # Use v2 cryptocurrency/ohlcv/historical for daily data
        data = self._get("/v2/cryptocurrency/ohlcv/historical", {
            "symbol": symbol,
            "count": count,
            "interval": "daily",
        })
        points = []
        for quote in data["data"]["quotes"]:
            usd = quote["quote"]["USD"]
            points.append(PricePoint(
                timestamp=quote["time_close"],
                price=usd["close"],
                volume_24h=usd["volume"],
                market_cap=usd["market_cap"],
                percent_change_24h=usd.get("percent_change_24h", 0),
            ))
        return points

    def get_fear_greed_index(self) -> int:
        """Fetch CMC Fear & Greed Index."""
        try:
            data = self._get("/v3/fear-and-greed/latest", {})
            return data["data"]["value"]
        except Exception:
            return 50  # neutral fallback

    def get_top_gainers_losers(self, limit: int = 10) -> dict:
        """Get top gainers and losers for whale-tracking context."""
        data = self._get("/v1/cryptocurrency/trending/gainers-losers", {"limit": limit})
        return {
            "gainers": [
                {"symbol": c["symbol"], "change": c["quote"]["USD"]["percent_change_24h"]}
                for c in data["data"]["gainers"]
            ],
            "losers": [
                {"symbol": c["symbol"], "change": c["quote"]["USD"]["percent_change_24h"]}
                for c in data["data"]["losers"]
            ],
        }
