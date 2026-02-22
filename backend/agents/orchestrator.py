"""Orchestrator: chains all agents, manages SSE event stream."""
import json
import logging
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi import Request

from config import PEER_TICKERS, ALL_TICKERS, EXCEL_PATH
from agents.research import search_analyst_bio, search_peer_research
from agents.forecast import read_forecast_data
from agents.market_data import get_valuation_data
from agents.sec_edgar import get_transcript
from agents.drafting import (
    generate_section,
    edit_section,
    edit_forecast_table,
    run_quality_check,
    format_search_results,
    format_peer_results,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_serializable(obj):
    """Recursively convert non-JSON-serializable types (numpy, pandas) to native Python."""
    import numbers
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, numbers.Number):
        if isinstance(obj, numbers.Integral):
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    return str(obj)


def _sse_event(event: str, data: dict) -> dict:
    """Format an SSE event. Pre-serialize to JSON string so sse-starlette sends it as-is."""
    return {"event": event, "data": json.dumps(_make_serializable(data))}


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return domain if domain else url[:40]
    except Exception:
        return url[:40]


def _top_sources(search_results: list[dict], max_n: int = 5) -> list[dict]:
    """Extract top unique-domain sources from search results."""
    sources = []
    seen = set()
    for r in search_results:
        url = r.get("href", "")
        if not url:
            continue
        domain = _extract_domain(url)
        if domain and domain not in seen:
            seen.add(domain)
            sources.append({
                "url": url,
                "domain": domain,
                "label": (r.get("title", "") or domain)[:80],
            })
        if len(sources) >= max_n:
            break
    return sources


def _confidence(level: str, reason: str) -> dict:
    """Build a confidence indicator dict."""
    return {"level": level, "reason": reason}


def _parse_ticker_changes(instruction: str, current_tickers: list[str]) -> list[str]:
    """Parse user instruction for ticker changes and return the updated ticker list.

    Supported patterns:
      - "Replace X with Y" / "Swap X for Y"
      - "Add X" / "Add X as a peer"
      - "Remove X" / "Drop X"
      - Multiple changes separated by commas/and (e.g. "Replace SCHW with BLK and add HOOD")

    The first ticker (target company, e.g. MS) is always preserved at index 0.
    Returns the original list unchanged if no ticker patterns are recognized.
    """
    if not instruction:
        return current_tickers

    text = instruction.upper()
    tickers = list(current_tickers)  # copy
    target = tickers[0] if tickers else "MS"
    changed = False

    # Replace / Swap patterns: "replace X with Y", "swap X for Y"
    for m in re.finditer(r'(?:REPLACE|SWAP)\s+([A-Z]{1,5})\s+(?:WITH|FOR)\s+([A-Z]{1,5})', text):
        old, new = m.group(1), m.group(2)
        if old in tickers and old != target:
            idx = tickers.index(old)
            tickers[idx] = new
            changed = True

    # Add patterns: "add X", "add X as a peer", "include X"
    for m in re.finditer(r'(?:ADD|INCLUDE)\s+([A-Z]{1,5})', text):
        new = m.group(1)
        if new not in tickers:
            tickers.append(new)
            changed = True

    # Remove / Drop patterns: "remove X", "drop X", "exclude X"
    for m in re.finditer(r'(?:REMOVE|DROP|EXCLUDE)\s+([A-Z]{1,5})', text):
        old = m.group(1)
        if old in tickers and old != target:
            tickers.remove(old)
            changed = True

    return tickers if changed else current_tickers


# ---------------------------------------------------------------------------
# Step hierarchy builder
# ---------------------------------------------------------------------------

def _build_steps(selected: list[str]) -> list[dict]:
    """Build the hierarchical step list based on selected sections."""
    steps = []
    if "bio" in selected:
        steps.append({
            "id": "bio",
            "label": "Analyst Background",
            "children": [
                {"id": "bio_search", "label": "Searching for analyst background"},
                {"id": "bio_draft", "label": "Drafting bio section with Claude"},
            ],
        })
    if "forecast" in selected:
        steps.append({
            "id": "forecast",
            "label": "Analyst Forecast",
            "children": [
                {"id": "forecast_read", "label": "Reading analyst forecast from Excel"},
                {"id": "forecast_deltas", "label": "Calculating consensus deltas"},
            ],
        })
    if "earnings" in selected:
        steps.append({
            "id": "earnings",
            "label": "Post-Earnings Analysis",
            "children": [
                {"id": "transcript_fetch", "label": "Retrieving earnings transcript"},
                {"id": "transcript_extract", "label": "Extracting analyst questions"},
                {"id": "earnings_draft", "label": "Drafting post-earnings feedback"},
            ],
        })
    if "peer" in selected:
        steps.append({
            "id": "peer",
            "label": "Peer Research",
            "children": [
                {"id": "peer_search", "label": "Searching for recent peer commentary"},
                {"id": "peer_draft", "label": "Drafting peer research summary"},
            ],
        })
    if "valuation" in selected:
        steps.append({
            "id": "valuation",
            "label": "Valuation Ratios",
            "children": [
                {"id": "market_data", "label": "Pulling live valuation data"},
            ],
        })
    steps.append({
        "id": "qc",
        "label": "Quality Check",
        "children": [
            {"id": "quality_check", "label": "Running quality check"},
        ],
    })
    return steps


async def _run_step(step_id, coro):
    """Run a coroutine and return (step_id, result_or_error)."""
    try:
        result = await coro
        return step_id, result
    except Exception as e:
        logger.error(f"Step '{step_id}' failed: {e}")
        return step_id, {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_orchestrator(
    analyst_name: str,
    company: str,
    selected: list[str],
    request: Request,
    memo_store: dict,
):
    """Main orchestrator generator that yields SSE events."""
    try:
        async for event in _run_orchestrator_inner(analyst_name, company, selected, request, memo_store):
            yield event
    except Exception as e:
        logger.exception(f"Orchestrator crashed: {e}")
        yield _sse_event("server_error", {"message": f"Orchestrator error: {e}"})


async def _run_orchestrator_inner(
    analyst_name: str,
    company: str,
    selected: list[str],
    request: Request,
    memo_store: dict,
):
    """Inner orchestrator logic, separated so outer can catch errors."""
    import pandas as pd
    df = pd.read_excel(EXCEL_PATH, sheet_name="Forecasts")
    analyst_row = df[df["Analyst"].str.lower() == analyst_name.lower()]
    firm = analyst_row.iloc[0]["Firm"] if not analyst_row.empty else ""

    # Emit hierarchical step list
    steps = _build_steps(selected)
    yield _sse_event("steps", {"steps": steps})

    memo = {
        "analyst": analyst_name,
        "firm": firm,
        "company": company,
        "date": datetime.now().strftime("%B %d, %Y"),
        "sections": {},
    }
    metadata = {
        "valuation_timestamp": "N/A",
        "forecast_date_updated": "N/A",
        "transcript_source": "N/A",
    }
    data_results = {}

    # ---- Group 1: Analyst Background ----
    if "bio" in selected:
        # Sub-step 1a: Web search
        yield _sse_event("step_update", {"step": "bio_search", "status": "running"})
        _, result = await _run_step("bio", search_analyst_bio(analyst_name, firm))
        data_results["bio"] = result

        search_results = result.get("search_results", [])
        n_results = len(search_results)
        bio_sources = _top_sources(search_results, 5)
        bio_status = "complete" if result.get("status") == "success" else "error"

        yield _sse_event("step_update", {
            "step": "bio_search",
            "status": bio_status,
            "findings": {
                "summary": f"Found {n_results} web sources about {analyst_name}",
                "sources": bio_sources,
                "detail": f"Retrieved {n_results} results from 4 DuckDuckGo queries (incl. career history)",
            },
        })

        # Sub-step 1b: Claude drafting
        yield _sse_event("step_update", {"step": "bio_draft", "status": "running"})
        search_results_text = format_search_results(search_results)
        bio_section = await generate_section(
            "bio",
            "analyst_bio",
            {"analyst_name": analyst_name, "firm": firm, "search_results": search_results_text},
        )
        word_count = len(bio_section.get("content", "").split())

        # Validate career history completeness
        bio_content = bio_section.get("content", "")
        prior_exp_text = ""
        for line in bio_content.split("\n"):
            if "prior experience" in line.lower():
                # Extract text after the label (after the colon following **)
                colon_pos = line.find(":**")
                if colon_pos != -1:
                    prior_exp_text = line[colon_pos + 3:].strip()
                else:
                    prior_exp_text = line
                break

        # Count firms: split on commas/semicolons, each segment is roughly one firm
        firm_count = 0
        if prior_exp_text:
            segments = re.split(r'[;,]', prior_exp_text)
            firm_count = sum(1 for s in segments if len(s.strip()) > 2)

        career_incomplete = firm_count < 3

        # Compute confidence
        n_domains = len(bio_sources)
        if n_domains >= 3 and not career_incomplete:
            bio_confidence = _confidence("high", f"{n_domains} sources found")
        elif n_domains >= 3 and career_incomplete:
            bio_confidence = _confidence("medium", f"Career history may be incomplete — fewer than 3 prior firms identified")
        elif n_domains >= 1:
            bio_confidence = _confidence("medium", f"Only {n_domains} source{'s' if n_domains > 1 else ''} found")
        else:
            bio_confidence = _confidence("low", "No web sources found")

        # Attach sources + confidence to section
        bio_section["sources"] = bio_sources
        bio_section["confidence"] = bio_confidence
        memo["sections"]["bio"] = bio_section

        yield _sse_event("step_update", {
            "step": "bio_draft",
            "status": "complete",
            "findings": {
                "summary": f"Generated {word_count}-word analyst profile",
                "detail": f"Synthesized from {n_domains} unique source domains",
            },
        })
        yield _sse_event("section", {
            "section": "bio",
            "content": bio_section["content"],
            "type": "narrative",
            "sources": bio_sources,
            "confidence": bio_confidence,
        })

    # ---- Group 2: Analyst Forecast ----
    if "forecast" in selected:
        # Sub-step 2a: Read Excel
        yield _sse_event("step_update", {"step": "forecast_read", "status": "running"})
        _, result = await _run_step("forecast", read_forecast_data(analyst_name))
        data_results["forecast"] = result

        if result.get("status") == "success":
            date_updated = result.get("date_updated", "N/A")
            metadata["forecast_date_updated"] = date_updated
            table_rows = result.get("table_rows", [])
            n_metrics = len(table_rows)
            is_stale = result.get("is_stale", False)
            stale_note = " (STALE - >30 days)" if is_stale else ""

            missing_count = sum(
                1 for r in table_rows
                if r.get("analyst") is None or r.get("consensus") is None
            )

            forecast_sources = [{
                "domain": "analyst_key_metrics.xlsx",
                "url": "",
                "label": f"Row: {analyst_name}, {firm}, updated {date_updated}",
            }]

            # Build compact preview of key fields from Excel
            firmwide_row = next((r for r in table_rows if r["label"] == "Firmwide Revenues"), None)
            eps_row = next((r for r in table_rows if r["label"] == "EPS"), None)
            forecast_preview = {
                "type": "forecast_table",
                "rows": [
                    {"label": "Analyst", "value": str(result.get("analyst_name", analyst_name))},
                    {"label": "Firm", "value": str(result.get("firm", firm))},
                    {"label": "Date Updated", "value": date_updated},
                    {"label": "Firmwide Rev", "value": f"${firmwide_row['analyst']:,.0f}M" if firmwide_row and firmwide_row.get("analyst") else "[N/A]"},
                    {"label": "EPS", "value": f"${eps_row['analyst']}" if eps_row and eps_row.get("analyst") else "[N/A]"},
                    {"label": "Rating", "value": str(result.get("rating", "[N/A]"))},
                    {"label": "Price Target", "value": f"${result['price_target']}" if result.get("price_target") else "[N/A]"},
                ],
                "local_source": True,
            }

            yield _sse_event("step_update", {
                "step": "forecast_read",
                "status": "complete",
                "findings": {
                    "summary": f"Loaded {analyst_name}'s forecast (updated {date_updated}){stale_note}",
                    "sources": forecast_sources,
                    "detail": f"{n_metrics} forecast fields extracted, {missing_count} missing values",
                    "preview": forecast_preview,
                },
            })

            # Sub-step 2b: Calculate deltas
            yield _sse_event("step_update", {"step": "forecast_deltas", "status": "running"})
            delta_count = sum(
                1 for r in table_rows
                if r.get("delta") and r["delta"] != "[Value unavailable]"
            )
            yield _sse_event("step_update", {
                "step": "forecast_deltas",
                "status": "complete",
                "findings": {
                    "summary": f"Computed delta % for {delta_count} of {n_metrics} metrics vs. consensus",
                },
            })

            # Compute confidence
            if is_stale and missing_count > 0:
                fc_confidence = _confidence("low", f"Data is stale and {missing_count} values missing")
            elif is_stale:
                fc_confidence = _confidence("medium", f"Data is older than 30 days (updated {date_updated})")
            elif missing_count > 2:
                fc_confidence = _confidence("medium", f"{missing_count} forecast values missing")
            else:
                fc_confidence = _confidence("high", f"Data current, {missing_count} missing values")

            result["sources"] = forecast_sources
            result["confidence"] = fc_confidence
            yield _sse_event("forecast", result)
            memo["sections"]["forecast"] = result
        else:
            yield _sse_event("step_update", {
                "step": "forecast_read",
                "status": "error",
                "findings": {
                    "summary": result.get("error", "Failed to read forecast data"),
                },
            })
            yield _sse_event("step_update", {
                "step": "forecast_deltas",
                "status": "error",
                "findings": {"summary": "Skipped — forecast data unavailable"},
            })
            memo["sections"]["forecast"] = {
                "error": result.get("error", "Failed"),
                "sources": [],
                "confidence": _confidence("low", "Forecast data unavailable"),
            }

    # ---- Group 3: Post-Earnings Analysis ----
    if "earnings" in selected:
        # Sub-step 3a: Retrieve transcript
        yield _sse_event("step_update", {"step": "transcript_fetch", "status": "running"})
        _, result = await _run_step("earnings", get_transcript(company, "Morgan Stanley"))
        data_results["earnings"] = result
        transcript_text = result.get("transcript_text", "")
        source = result.get("source", "N/A")
        source_url = result.get("source_url", "")
        tier = result.get("tier", 0)
        metadata["transcript_source"] = source

        transcript_sources = []
        if result.get("status") == "success" and transcript_text:
            char_count = len(transcript_text)
            transcript_sources = [{
                "domain": source,
                "url": source_url,
                "label": f"Transcript from {source} ({char_count:,} characters)",
            }]
            tier_label = f" [Tier {tier}]" if tier else ""

            # Build transcript snippet preview — find the analyst's first Q&A
            transcript_preview = None
            if tier == 5:
                snippet_lines = transcript_text.split("\n")
                analyst_first = analyst_name.split()[-1]  # e.g. "Mayo" from "Mike Mayo"
                snippet_start = None
                for i, line in enumerate(snippet_lines):
                    if analyst_first.lower() in line.lower() and ":" in line:
                        snippet_start = i
                        break
                if snippet_start is not None:
                    # Grab the operator intro + analyst question (up to 6 lines)
                    start = max(0, snippet_start - 1)
                    end = min(len(snippet_lines), snippet_start + 5)
                    snippet = "\n".join(snippet_lines[start:end])
                    transcript_preview = {
                        "type": "transcript_snippet",
                        "analyst_name": analyst_name,
                        "snippet": snippet,
                        "char_count": char_count,
                        "local_source": True,
                    }

            yield _sse_event("step_update", {
                "step": "transcript_fetch",
                "status": "complete",
                "findings": {
                    "summary": f"Retrieved {char_count:,}-character transcript from {source}{tier_label}",
                    "sources": transcript_sources,
                    "detail": f"Fallback chain: SEC EDGAR → FMP API → Web → Local file (resolved at tier {tier})",
                    **({"preview": transcript_preview} if transcript_preview else {}),
                },
            })
        else:
            transcript_sources = []
            yield _sse_event("step_update", {
                "step": "transcript_fetch",
                "status": "error",
                "findings": {
                    "summary": "Transcript not available from public sources",
                    "detail": "Tried all 5 tiers: SEC EDGAR (EFTS, 8-K), FMP API, web search, local file",
                },
            })

        # Sub-step 3b: Extract analyst questions
        yield _sse_event("step_update", {"step": "transcript_extract", "status": "running"})
        if not transcript_text:
            transcript_text = "[Earnings call transcript not available from public sources]"
        yield _sse_event("step_update", {
            "step": "transcript_extract",
            "status": "complete",
            "findings": {
                "summary": f"Processing transcript for {analyst_name}'s Q&A",
            },
        })

        # Sub-step 3c: Claude drafting
        yield _sse_event("step_update", {"step": "earnings_draft", "status": "running"})
        earnings_section = await generate_section(
            "earnings",
            "earnings_feedback",
            {"analyst_name": analyst_name, "firm": firm, "transcript_text": transcript_text[:15000]},
        )
        word_count = len(earnings_section.get("content", "").split())

        # Count extracted questions (blockquotes starting with >)
        earnings_content = earnings_section.get("content", "")
        question_count = len(re.findall(r'^>\s*"', earnings_content, re.MULTILINE))
        limited_participation = question_count < 2

        # Compute confidence
        has_transcript = bool(result.get("status") == "success" and result.get("transcript_text"))
        is_snippets = "[Partial transcript" in transcript_text
        is_local_file = tier == 5
        if not has_transcript:
            earnings_confidence = _confidence("low", "Transcript not available")
        elif limited_participation:
            earnings_confidence = _confidence("medium", "Limited analyst participation found in transcript")
        elif is_local_file:
            earnings_confidence = _confidence("medium", "Using bundled demo transcript (live sources unavailable)")
        elif is_snippets:
            earnings_confidence = _confidence("medium", "Only web search snippets available")
        else:
            earnings_confidence = _confidence("high", f"Full transcript retrieved from {source}")

        earnings_section["sources"] = transcript_sources
        earnings_section["confidence"] = earnings_confidence
        memo["sections"]["earnings"] = earnings_section

        yield _sse_event("step_update", {
            "step": "earnings_draft",
            "status": "complete",
            "findings": {
                "summary": f"Generated {word_count}-word post-earnings analysis",
                "sources": transcript_sources,
            },
        })
        yield _sse_event("section", {
            "section": "earnings",
            "content": earnings_section["content"],
            "type": "narrative",
            "sources": transcript_sources,
            "confidence": earnings_confidence,
        })

    # ---- Group 4: Peer Research ----
    if "peer" in selected:
        # Sub-step 4a: Web search
        yield _sse_event("step_update", {"step": "peer_search", "status": "running"})
        _, result = await _run_step("peer", search_peer_research(analyst_name, PEER_TICKERS))
        data_results["peer"] = result

        # Collect all unique sources from peer results
        all_peer_search_results = []
        for ticker, results_list in result.get("peer_results", {}).items():
            all_peer_search_results.extend(results_list)
        all_peer_search_results.extend(result.get("sector_results", []))

        peer_sources = _top_sources(all_peer_search_results, 5)
        n_peers_with_results = len([
            t for t, r in result.get("peer_results", {}).items() if r
        ])
        n_total_results = len(all_peer_search_results)

        yield _sse_event("step_update", {
            "step": "peer_search",
            "status": "complete" if result.get("status") == "success" else "error",
            "findings": {
                "summary": f"Found commentary on {n_peers_with_results} peer tickers + sector overview",
                "sources": peer_sources,
                "detail": f"Retrieved {n_total_results} total results across {len(PEER_TICKERS)} peers",
            },
        })

        # Sub-step 4b: Claude drafting
        yield _sse_event("step_update", {"step": "peer_draft", "status": "running"})
        peer_data = data_results.get("peer", {})
        peer_results_text = format_peer_results(
            peer_data.get("peer_results", {}),
            peer_data.get("sector_results", []),
        )
        peer_section = await generate_section(
            "peer",
            "peer_research",
            {"analyst_name": analyst_name, "firm": firm, "peer_results": peer_results_text},
        )
        word_count = len(peer_section.get("content", "").split())

        # Extract publication date from peer content for staleness check
        peer_content = peer_section.get("content", "")
        peer_date_parsed = None
        peer_date_str = ""

        # Look for date in structured output — handles both:
        #   table row:  | **Date** | October 2024 |
        #   bullet:     **Date:** October 2024
        date_match = re.search(
            r'\|\s*\*?\*?Date\*?\*?\s*\|\s*(.+?)\s*\|',
            peer_content,
            re.IGNORECASE,
        )
        if not date_match:
            date_match = re.search(
                r'\*?\*?Date:?\*?\*?\s*(.+)',
                peer_content,
                re.IGNORECASE,
            )
        if date_match:
            peer_date_str = date_match.group(1).strip().rstrip("*|").strip()
            # Try parsing common date formats
            for fmt in ("%B %Y", "%b %Y", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
                try:
                    peer_date_parsed = datetime.strptime(peer_date_str, fmt)
                    break
                except ValueError:
                    continue

        # Compute staleness in months
        peer_stale_note = None
        if peer_date_parsed:
            now = datetime.now()
            months_old = (now.year - peer_date_parsed.year) * 12 + (now.month - peer_date_parsed.month)
            if months_old > 6:
                peer_stale_note = f"Most recent commentary found is from {peer_date_str} — may not reflect current views"
            elif months_old >= 3:
                peer_stale_note = f"Commentary is {months_old} months old"
        else:
            if peer_content and n_peers_with_results >= 1:
                peer_stale_note = "Publication date could not be verified"

        # Compute confidence — factor in staleness
        n_domains = len(peer_sources)
        if peer_stale_note:
            # Staleness caps confidence at medium
            peer_confidence = _confidence("medium", peer_stale_note)
        elif n_peers_with_results >= 3 and n_domains >= 2:
            peer_confidence = _confidence("high", f"Recent commentary found from {n_peers_with_results} peers")
        elif n_peers_with_results >= 1:
            peer_confidence = _confidence("medium", f"Limited results — {n_peers_with_results} peer{'s' if n_peers_with_results > 1 else ''} with data")
        else:
            peer_confidence = _confidence("low", "No peer commentary found")

        peer_section["sources"] = peer_sources
        peer_section["confidence"] = peer_confidence
        memo["sections"]["peer"] = peer_section

        yield _sse_event("step_update", {
            "step": "peer_draft",
            "status": "complete",
            "findings": {
                "summary": f"Generated {word_count}-word peer research summary",
                "detail": f"Synthesized from {n_domains} unique source domains",
            },
        })
        yield _sse_event("section", {
            "section": "peer",
            "content": peer_section["content"],
            "type": "narrative",
            "sources": peer_sources,
            "confidence": peer_confidence,
        })

    # ---- Group 5: Valuation Ratios ----
    if "valuation" in selected:
        yield _sse_event("step_update", {"step": "market_data", "status": "running"})
        _, result = await _run_step("valuation", get_valuation_data(ALL_TICKERS))
        data_results["valuation"] = result

        if result.get("status") == "success":
            tickers_data = result.get("tickers", {})
            n_tickers = len(tickers_data)
            as_of = result.get("as_of", "N/A")
            metadata["valuation_timestamp"] = as_of

            # Count failures (tickers where Stock Price is None)
            n_failures = sum(
                1 for d in tickers_data.values()
                if d.get("Stock Price") is None
            )
            ms_price = tickers_data.get("MS", {}).get("Stock Price")
            ms_price_str = f"${ms_price:.2f}" if ms_price else "N/A"

            valuation_sources = [{
                "domain": "Yahoo Finance API",
                "url": "",
                "label": f"Real-time data — MS: {ms_price_str} (as of {as_of})",
            }]

            # Compute confidence
            if n_failures == 0:
                val_confidence = _confidence("high", f"All {n_tickers} tickers retrieved")
            elif n_failures <= 2:
                val_confidence = _confidence("medium", f"{n_failures} of {n_tickers} tickers failed")
            else:
                val_confidence = _confidence("low", f"Major data gaps — {n_failures} tickers failed")

            result["sources"] = valuation_sources
            result["confidence"] = val_confidence

            yield _sse_event("step_update", {
                "step": "market_data",
                "status": "complete",
                "findings": {
                    "summary": f"Pulled live data for {n_tickers} tickers as of {as_of}",
                    "sources": valuation_sources,
                    "detail": f"Retrieved data for {n_tickers} tickers, {n_failures} failures",
                },
            })
            yield _sse_event("valuation", result)
            memo["sections"]["valuation"] = result
        else:
            yield _sse_event("step_update", {
                "step": "market_data",
                "status": "error",
                "findings": {
                    "summary": result.get("error", "Failed to pull valuation data"),
                },
            })
            memo["sections"]["valuation"] = {
                "error": result.get("error", "Failed"),
                "sources": [],
                "confidence": _confidence("low", "Valuation data unavailable"),
            }

    # ---- Group 6: Quality Check ----
    yield _sse_event("step_update", {"step": "quality_check", "status": "running"})

    sections_summary = {}
    for key, val in memo["sections"].items():
        if isinstance(val, dict) and "content" in val:
            sections_summary[key] = val["content"]
        elif isinstance(val, dict) and "table_rows" in val:
            rows_text = []
            for r in val["table_rows"]:
                rows_text.append(f"{r['label']}: Analyst={r['analyst']}, Consensus={r['consensus']}, Delta={r['delta']}")
            rows_text.append(f"Rating: {val.get('rating', 'N/A')}, Price Target: ${val.get('price_target', 'N/A')}")
            rows_text.append(f"Date Updated: {val.get('date_updated', 'N/A')}")
            sections_summary[key] = "Forecast table data:\n" + "\n".join(rows_text)
        elif isinstance(val, dict) and "tickers" in val:
            ticker_lines = []
            for ticker, metrics in val.get("tickers", {}).items():
                price = metrics.get("Stock Price", "N/A")
                pe = metrics.get("P/E (TTM)", "N/A")
                ticker_lines.append(f"{ticker}: Price=${price}, P/E={pe}")
            sections_summary[key] = f"Live valuation data as of {val.get('as_of', 'N/A')}:\n" + "\n".join(ticker_lines)
        else:
            sections_summary[key] = str(val)[:500]

    metadata["today_date"] = datetime.now().strftime("%Y-%m-%d")
    qc_result = await run_quality_check(sections_summary, metadata)
    yield _sse_event("quality_check", qc_result)
    memo["quality_check"] = qc_result

    overall = qc_result.get("overall_status", "unknown")
    summary = qc_result.get("summary", "")
    findings_text = f"{overall.upper()}"
    if summary:
        findings_text += f" — {summary[:100]}"
    yield _sse_event("step_update", {
        "step": "quality_check",
        "status": "complete",
        "findings": {
            "summary": findings_text,
        },
    })

    # ---- Final: Store and Complete ----
    memo_id = str(uuid.uuid4())[:8]
    memo_store[memo_id] = memo

    yield _sse_event("complete", {"memo_id": memo_id})


# ---------------------------------------------------------------------------
# Per-section regeneration
# ---------------------------------------------------------------------------

async def run_regeneration(
    section: str,
    analyst_name: str,
    instruction: str,
    re_search: bool,
    original_data: dict,
    memo_store: dict,
    memo_id: str,
    current_content: str = "",
):
    """Regenerate a single section. Yields SSE events scoped to that section."""
    try:
        async for event in _run_regeneration_inner(
            section, analyst_name, instruction, re_search, original_data,
            memo_store, memo_id, current_content,
        ):
            yield event
    except Exception as e:
        logger.exception(f"Regeneration crashed for section '{section}': {e}")
        yield _sse_event("regen_error", {"section": section, "message": str(e)})


async def _run_regeneration_inner(
    section: str,
    analyst_name: str,
    instruction: str,
    re_search: bool,
    original_data: dict,
    memo_store: dict,
    memo_id: str,
    current_content: str = "",
):
    """Inner regeneration logic.

    Two modes:
      - draft-only (re_search=false): Edit existing content via Claude using current_content + instruction.
      - re-search (re_search=true): Full pipeline re-run with new data + instruction.
    """
    memo = memo_store.get(memo_id)
    if not memo:
        yield _sse_event("regen_error", {"section": section, "message": "Memo not found"})
        return

    firm = memo.get("firm", "")
    existing_section = memo.get("sections", {}).get(section, {})

    yield _sse_event("regen_start", {"section": section})

    # ---------------------------------------------------------------
    # DRAFT-ONLY MODE: edit existing content, don't re-run pipeline
    # ---------------------------------------------------------------
    if not re_search:
        # Narrative sections (bio, earnings, peer) — edit via Claude
        if section in ("bio", "earnings", "peer"):
            content_to_edit = current_content or existing_section.get("content", "")
            if not content_to_edit:
                yield _sse_event("regen_error", {"section": section, "message": "No existing content to edit"})
                return

            yield _sse_event("regen_step", {"section": section, "step": "Applying changes with Claude"})
            edited = await edit_section(section, content_to_edit, instruction)

            # Preserve existing sources and confidence from the original section
            sources = existing_section.get("sources", [])
            confidence = existing_section.get("confidence", _confidence("medium", "Edited section"))

            edited["sources"] = sources
            edited["confidence"] = confidence
            memo["sections"][section] = edited

            yield _sse_event("regen_section", {
                "section": section,
                "content": edited["content"],
                "sources": sources,
                "confidence": confidence,
            })

        # Forecast — apply structural/formatting changes via Claude
        elif section == "forecast":
            # Start from existing table data (no re-read needed for draft-only)
            existing_rows = existing_section.get("table_rows", [])
            if not existing_rows:
                yield _sse_event("regen_error", {"section": section, "message": "No existing forecast data to edit"})
                return

            if instruction:
                yield _sse_event("regen_step", {"section": section, "step": "Applying changes to forecast table"})
                modified_rows = await edit_forecast_table(existing_rows, instruction)
                if modified_rows:
                    result = {**existing_section, "table_rows": modified_rows}
                else:
                    # Claude failed — return existing data unchanged
                    result = existing_section
            else:
                result = existing_section

            sources = existing_section.get("sources", [])
            confidence = existing_section.get("confidence", _confidence("medium", "Edited forecast"))
            result["sources"] = sources
            result["confidence"] = confidence
            memo["sections"]["forecast"] = result
            yield _sse_event("regen_forecast", result)

        # Valuation — check if tickers need to change
        elif section == "valuation":
            existing_tickers = list(existing_section.get("tickers", {}).keys()) if existing_section.get("tickers") else list(ALL_TICKERS)
            new_tickers = _parse_ticker_changes(instruction, existing_tickers)

            if new_tickers != existing_tickers:
                # Tickers changed — must re-pull from Yahoo Finance
                yield _sse_event("regen_step", {"section": section, "step": f"Pulling data for updated tickers: {', '.join(new_tickers)}"})
                _, result = await _run_step("valuation", get_valuation_data(new_tickers))

                if result.get("status") == "success":
                    tickers_data = result.get("tickers", {})
                    as_of = result.get("as_of", "N/A")
                    target = new_tickers[0]
                    target_price = tickers_data.get(target, {}).get("Stock Price")
                    target_price_str = f"${target_price:.2f}" if target_price else "N/A"

                    valuation_sources = [{
                        "domain": "Yahoo Finance API",
                        "url": "",
                        "label": f"Real-time data — {target}: {target_price_str} (as of {as_of})",
                    }]
                    n_failures = sum(1 for d in tickers_data.values() if d.get("Stock Price") is None)
                    val_confidence = _confidence("high", f"All {len(tickers_data)} tickers retrieved") if n_failures == 0 \
                        else _confidence("medium", f"{n_failures} tickers failed")

                    result["sources"] = valuation_sources
                    result["confidence"] = val_confidence
                    result["ticker_order"] = new_tickers
                    memo["sections"]["valuation"] = result
                    yield _sse_event("regen_valuation", result)
                else:
                    yield _sse_event("regen_error", {"section": section, "message": "Failed to pull valuation data"})
                    return
            else:
                # No ticker changes — return existing data unchanged
                result = existing_section
                if result.get("tickers"):
                    yield _sse_event("regen_valuation", result)
                else:
                    yield _sse_event("regen_error", {"section": section, "message": "No existing valuation data"})
                    return

        else:
            yield _sse_event("regen_error", {"section": section, "message": f"Unknown section: {section}"})
            return

        yield _sse_event("regen_complete", {"section": section})
        return

    # ---------------------------------------------------------------
    # RE-SEARCH MODE: full pipeline re-run with new data
    # ---------------------------------------------------------------

    # --- Bio ---
    if section == "bio":
        yield _sse_event("regen_step", {"section": section, "step": "Searching for analyst background"})
        _, result = await _run_step("bio", search_analyst_bio(analyst_name, firm))
        search_results = result.get("search_results", [])

        yield _sse_event("regen_step", {"section": section, "step": "Drafting bio section with Claude"})
        search_results_text = format_search_results(search_results)
        bio_section = await generate_section(
            "bio", "analyst_bio",
            {"analyst_name": analyst_name, "firm": firm, "search_results": search_results_text},
            user_instruction=instruction,
        )

        bio_sources = _top_sources(search_results, 5)
        n_domains = len(bio_sources)
        bio_confidence = _confidence("high", f"{n_domains} sources found") if n_domains >= 3 else \
            _confidence("medium", f"Only {n_domains} source{'s' if n_domains > 1 else ''} found") if n_domains >= 1 else \
            _confidence("low", "No web sources found")

        bio_section["sources"] = bio_sources
        bio_section["confidence"] = bio_confidence
        memo["sections"]["bio"] = bio_section

        yield _sse_event("regen_section", {
            "section": "bio",
            "content": bio_section["content"],
            "sources": bio_sources,
            "confidence": bio_confidence,
        })

    # --- Forecast ---
    elif section == "forecast":
        yield _sse_event("regen_step", {"section": section, "step": "Re-reading forecast from Excel"})
        _, result = await _run_step("forecast", read_forecast_data(analyst_name))

        if result.get("status") == "success":
            # Apply user instruction to modify table structure/formatting
            if instruction:
                yield _sse_event("regen_step", {"section": section, "step": "Applying changes to forecast table"})
                modified_rows = await edit_forecast_table(result.get("table_rows", []), instruction)
                if modified_rows:
                    result["table_rows"] = modified_rows

            date_updated = result.get("date_updated", "N/A")
            is_stale = result.get("is_stale", False)
            forecast_sources = [{
                "domain": "analyst_key_metrics.xlsx",
                "url": "",
                "label": f"Row: {analyst_name}, {firm}, updated {date_updated}",
            }]
            fc_confidence = _confidence("medium", f"Data is older than 30 days (updated {date_updated})") if is_stale \
                else _confidence("high", "Data current")

            result["sources"] = forecast_sources
            result["confidence"] = fc_confidence
            memo["sections"]["forecast"] = result

            yield _sse_event("regen_forecast", result)
        else:
            yield _sse_event("regen_error", {"section": section, "message": "Failed to read forecast data"})
            return

    # --- Earnings ---
    elif section == "earnings":
        yield _sse_event("regen_step", {"section": section, "step": "Re-fetching earnings transcript"})
        _, result = await _run_step("earnings", get_transcript("MS", "Morgan Stanley"))
        transcript_text = result.get("transcript_text", "")
        source = result.get("source", "N/A")
        source_url = result.get("source_url", "")

        if not transcript_text:
            transcript_text = "[Earnings call transcript not available from public sources]"

        yield _sse_event("regen_step", {"section": section, "step": "Drafting post-earnings feedback"})
        earnings_section = await generate_section(
            "earnings", "earnings_feedback",
            {"analyst_name": analyst_name, "firm": firm, "transcript_text": transcript_text[:15000]},
            user_instruction=instruction,
        )

        transcript_sources = [{
            "domain": source,
            "url": source_url,
            "label": f"Transcript from {source}",
        }] if transcript_text and "[not available" not in transcript_text else []

        earnings_confidence = _confidence("medium", "Regenerated section")
        earnings_section["sources"] = transcript_sources
        earnings_section["confidence"] = earnings_confidence
        memo["sections"]["earnings"] = earnings_section

        yield _sse_event("regen_section", {
            "section": "earnings",
            "content": earnings_section["content"],
            "sources": transcript_sources,
            "confidence": earnings_confidence,
        })

    # --- Peer Research ---
    elif section == "peer":
        yield _sse_event("regen_step", {"section": section, "step": "Searching for peer commentary"})
        _, result = await _run_step("peer", search_peer_research(analyst_name, PEER_TICKERS))
        all_peer_search_results = []
        for ticker, results_list in result.get("peer_results", {}).items():
            all_peer_search_results.extend(results_list)
        all_peer_search_results.extend(result.get("sector_results", []))
        peer_results_text = format_peer_results(
            result.get("peer_results", {}), result.get("sector_results", [])
        )

        yield _sse_event("regen_step", {"section": section, "step": "Drafting peer research summary"})
        peer_section = await generate_section(
            "peer", "peer_research",
            {"analyst_name": analyst_name, "firm": firm, "peer_results": peer_results_text},
            user_instruction=instruction,
        )

        peer_sources = _top_sources(all_peer_search_results, 5)
        n_domains = len(peer_sources)
        peer_confidence = _confidence("high", f"Commentary from {n_domains} sources") if n_domains >= 2 \
            else _confidence("medium", "Limited sources") if n_domains >= 1 \
            else _confidence("low", "No peer commentary found")

        peer_section["sources"] = peer_sources
        peer_section["confidence"] = peer_confidence
        memo["sections"]["peer"] = peer_section

        yield _sse_event("regen_section", {
            "section": "peer",
            "content": peer_section["content"],
            "sources": peer_sources,
            "confidence": peer_confidence,
        })

    # --- Valuation ---
    elif section == "valuation":
        existing_tickers = list(existing_section.get("tickers", {}).keys()) if existing_section.get("tickers") else list(ALL_TICKERS)
        new_tickers = _parse_ticker_changes(instruction, existing_tickers)

        yield _sse_event("regen_step", {"section": section, "step": f"Pulling fresh valuation data for {', '.join(new_tickers)}"})
        _, result = await _run_step("valuation", get_valuation_data(new_tickers))

        if result.get("status") == "success":
            tickers_data = result.get("tickers", {})
            as_of = result.get("as_of", "N/A")
            target = new_tickers[0]
            target_price = tickers_data.get(target, {}).get("Stock Price")
            target_price_str = f"${target_price:.2f}" if target_price else "N/A"

            valuation_sources = [{
                "domain": "Yahoo Finance API",
                "url": "",
                "label": f"Real-time data — {target}: {target_price_str} (as of {as_of})",
            }]

            n_failures = sum(1 for d in tickers_data.values() if d.get("Stock Price") is None)
            val_confidence = _confidence("high", f"All {len(tickers_data)} tickers retrieved") if n_failures == 0 \
                else _confidence("medium", f"{n_failures} tickers failed")

            result["sources"] = valuation_sources
            result["confidence"] = val_confidence
            result["ticker_order"] = new_tickers
            memo["sections"]["valuation"] = result

            yield _sse_event("regen_valuation", result)
        else:
            yield _sse_event("regen_error", {"section": section, "message": "Failed to pull valuation data"})
            return

    else:
        yield _sse_event("regen_error", {"section": section, "message": f"Unknown section: {section}"})
        return

    yield _sse_event("regen_complete", {"section": section})
