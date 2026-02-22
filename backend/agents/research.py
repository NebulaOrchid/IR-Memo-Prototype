"""DuckDuckGo web search agent for analyst bio and peer research."""
import asyncio
import logging
from ddgs import DDGS

logger = logging.getLogger(__name__)


def _search(query: str, max_results: int = 8) -> list[dict]:
    """Run a single DuckDuckGo text search (synchronous)."""
    try:
        results = DDGS().text(query, max_results=max_results)
        return results if results else []
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
        return []


async def search_analyst_bio(analyst_name: str, firm: str) -> dict:
    """Search for analyst bio, career history, and recent commentary.

    Returns:
        {"analyst_name", "firm", "search_results": [{"title", "body", "href"}, ...]}
    """
    queries = [
        f'"{analyst_name}" "{firm}" analyst bio coverage universe',
        f'"{analyst_name}" analyst banking interview commentary',
        f'"{analyst_name}" career history banks analyst',
        f'"{analyst_name}" BrokerCheck prior firms employment history',
    ]

    all_results = []
    seen_urls = set()

    for query in queries:
        results = await asyncio.to_thread(_search, query, 8)
        for r in results:
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": url,
                })
        await asyncio.sleep(1)  # Rate limit spacing

    return {
        "status": "success",
        "analyst_name": analyst_name,
        "firm": firm,
        "search_results": all_results,
    }


async def search_peer_research(analyst_name: str, peer_tickers: list[str]) -> dict:
    """Search for analyst's recent commentary on peer banks.

    Returns:
        {"analyst_name", "peer_results": {ticker: [results]}, "sector_results": [results]}
    """
    peer_results = {}

    # Search per peer ticker
    for ticker in peer_tickers:
        query = f'"{analyst_name}" {ticker} research outlook rating'
        results = await asyncio.to_thread(_search, query, 5)
        peer_results[ticker] = [
            {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
            for r in results
        ]
        await asyncio.sleep(1)

    # Broader sector search
    sector_query = f'"{analyst_name}" large bank sector outlook'
    sector_results_raw = await asyncio.to_thread(_search, sector_query, 5)
    sector_results = [
        {"title": r.get("title", ""), "body": r.get("body", ""), "href": r.get("href", "")}
        for r in sector_results_raw
    ]

    return {
        "status": "success",
        "analyst_name": analyst_name,
        "peer_results": peer_results,
        "sector_results": sector_results,
    }
