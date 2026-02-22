"""Yahoo Finance market data agent for valuation ratios."""
import asyncio
import logging
import statistics
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)

# (display_label, yfinance_key, transform_fn)
METRICS = [
    ("Stock Price", "currentPrice", None),
    ("P/E (TTM)", "trailingPE", None),
    ("Forward P/E", "forwardPE", None),
    ("Price/Book", "priceToBook", None),
    ("Dividend Yield", "dividendYield", lambda x: round(x, 2) if x else None),
    ("Market Cap ($B)", "marketCap", lambda x: round(x / 1e9, 1) if x else None),
    ("52W High", "fiftyTwoWeekHigh", None),
    ("52W Low", "fiftyTwoWeekLow", None),
]


async def _fetch_ticker(ticker: str) -> dict:
    """Fetch valuation data for a single ticker."""
    try:
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        row = {}
        for label, key, transform in METRICS:
            val = info.get(key)
            if val is not None and transform:
                val = transform(val)
            row[label] = val
        return row
    except Exception as e:
        logger.warning(f"Failed to fetch data for {ticker}: {e}")
        return {label: None for label, _, _ in METRICS}


async def get_valuation_data(tickers: list[str]) -> dict:
    """Pull live valuation data for all tickers in parallel.

    Returns:
        {
            "status": "success"/"error",
            "tickers": {ticker: {metric: value, ...}, ...},
            "as_of": "YYYY-MM-DD HH:MM ET",
            "peer_median": {metric: value, ...},
        }
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M ET")

    # Fetch all tickers in parallel
    tasks = [_fetch_ticker(t) for t in tickers]
    results = await asyncio.gather(*tasks)

    data = {}
    for ticker, result in zip(tickers, results):
        data[ticker] = result

    # Calculate peer median (exclude the first ticker which is the target company)
    target_ticker = tickers[0] if tickers else None
    peer_tickers = tickers[1:] if len(tickers) > 1 else []

    peer_median = {}
    for label, _, _ in METRICS:
        if label in ("52W High", "52W Low"):
            peer_median[label] = "-"
            continue
        vals = []
        for pt in peer_tickers:
            v = data.get(pt, {}).get(label)
            if v is not None:
                vals.append(v)
        if vals:
            raw = statistics.median(vals)
            peer_median[label] = float(Decimal(str(raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        else:
            peer_median[label] = None

    return {
        "status": "success",
        "tickers": data,
        "as_of": timestamp,
        "peer_median": peer_median,
    }
