"""
Mock data provider — generates realistic synthetic market data.
Falls back automatically when CMC API is unreachable or USE_MOCK_DATA=1.
"""
import math
import random
import time
from dataclasses import dataclass
from .cmc_client import MarketSnapshot, PricePoint


# Realistic prices around June 2026
BASE_PRICES: dict[str, float] = {
    "BNB": 620.0,
    "BTC": 87000.0,
    "ETH": 3400.0,
    "SOL": 180.0,
    "XRP": 2.40,
    "DOGE": 0.18,
}
DEFAULT_PRICE = 680.0
VOLATILITY = 0.03  # daily volatility


def generate_price_history(days: int = 90, seed: int = 42, symbol: str = "BNB") -> list[PricePoint]:
    """Generate realistic price history with trends, mean-reversion, and volume."""
    rng = random.Random(seed)
    base_price = BASE_PRICES.get(symbol, DEFAULT_PRICE)
    prices: list[float] = [base_price]
    base_ts = int(time.time()) - days * 86400

    # Generate price path with momentum + mean reversion + noise
    for i in range(1, days):
        # Cycle component (sine wave creates natural tops/bottoms)
        cycle = math.sin(i * 2 * math.pi / 50) * 0.008

        # Momentum component
        if len(prices) >= 3:
            momentum = (prices[-1] - prices[-3]) / prices[-3] * 0.25
        else:
            momentum = 0

        # Strong mean reversion keeps price near base
        mean_rev = (base_price - prices[-1]) / base_price * 0.04

        # Random noise
        noise = rng.gauss(0, VOLATILITY)

        daily_return = cycle + momentum + mean_rev + noise
        # Clamp daily moves to ±8%
        daily_return = max(-0.08, min(0.08, daily_return))
        new_price = prices[-1] * (1 + daily_return)
        # Keep within ±50% of base price
        new_price = max(base_price * 0.5, min(base_price * 1.5, new_price))
        prices.append(new_price)

    points = []
    for i in range(days):
        ts = base_ts + i * 86400
        # Volume: higher on volatile days
        vol_mult = 1.0 + abs((prices[i] - prices[i - 1]) / prices[i - 1]) * 20 if i > 0 else 1.0
        volume = 800_000_000 * vol_mult * rng.uniform(0.7, 1.3)
        mcap = prices[i] * 150_000_000  # ~150M BNB circulating

        # 24h change
        if i >= 1:
            change_24h = (prices[i] - prices[i - 1]) / prices[i - 1] * 100
        else:
            change_24h = 0

        points.append(PricePoint(
            timestamp=ts,
            price=round(prices[i], 2),
            volume_24h=volume,
            market_cap=mcap,
            percent_change_24h=round(change_24h, 2),
        ))

    return points


SYMBOL_SEEDS: dict[str, int] = {"BNB": 42, "BTC": 77, "ETH": 13, "SOL": 91, "XRP": 55, "DOGE": 33}

# Each count gets its own seed offset so price paths differ
def get_mock_snapshot(symbol: str = "BNB", count: int = 90) -> MarketSnapshot:
    """Get a realistic mock snapshot — price path varies with count."""
    base_seed = SYMBOL_SEEDS.get(symbol, 42)
    # Different count = different price path
    seed = base_seed + count * 7
    history = generate_price_history(count, seed=seed, symbol=symbol)
    current = history[-1]
    prev = history[-2] if len(history) > 1 else current

    # Calculate fear & greed based on recent trend
    recent_prices = [p.price for p in history[-14:]]
    trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100

    # Fear & Greed: -10% trend = fear (20), +10% = greed (80)
    fg = int(50 + trend * 3)
    fg = max(5, min(95, fg))

    # Add some randomness
    fg = max(5, min(95, fg + random.randint(-10, 10)))

    return MarketSnapshot(
        symbol=symbol,
        current_price=current.price,
        price_history=history,
        volume_24h=current.volume_24h,
        market_cap=current.market_cap,
        market_cap_dominance=3.5,
        fear_greed_index=fg,
    )
