"""Claude API drafting agent for generating memo sections and quality check."""
import asyncio
import json
import logging

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, PROMPTS_DIR

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def load_prompt(template_name: str, **kwargs) -> str:
    """Load a prompt template and format with provided variables."""
    path = PROMPTS_DIR / f"{template_name}.txt"
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(**kwargs)


def format_search_results(results: list[dict]) -> str:
    """Format DuckDuckGo search results into a numbered list for prompt injection."""
    if not results:
        return "[No search results available]"
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] Title: {r.get('title', 'N/A')}\n"
            f"    URL: {r.get('href', 'N/A')}\n"
            f"    Snippet: {r.get('body', 'N/A')}"
        )
    return "\n\n".join(formatted)


def format_peer_results(peer_results: dict, sector_results: list[dict]) -> str:
    """Format peer research results for prompt injection."""
    parts = []
    for ticker, results in peer_results.items():
        if results:
            parts.append(f"--- {ticker} ---")
            for i, r in enumerate(results, 1):
                parts.append(
                    f"[{i}] {r.get('title', 'N/A')}\n"
                    f"    URL: {r.get('href', 'N/A')}\n"
                    f"    {r.get('body', 'N/A')}"
                )
        else:
            parts.append(f"--- {ticker} ---\n[No results found]")
        parts.append("")

    if sector_results:
        parts.append("--- Sector-Level Research ---")
        for i, r in enumerate(sector_results, 1):
            parts.append(
                f"[{i}] {r.get('title', 'N/A')}\n"
                f"    URL: {r.get('href', 'N/A')}\n"
                f"    {r.get('body', 'N/A')}"
            )

    return "\n".join(parts) if parts else "[No peer research results available]"


_SECTION_MAX_TOKENS = {
    "earnings": 3000,  # Earnings Q&A can be long with multiple analyst turns
}


async def generate_section(
    section_name: str,
    template_name: str,
    context: dict,
    user_instruction: str = "",
) -> dict:
    """Generate a single memo section using Claude.

    Args:
        user_instruction: Optional additional instruction appended to the prompt
            (used for per-section regeneration).

    Returns:
        {"section": section_name, "content": str, "status": "success"/"error"}
    """
    max_tokens = _SECTION_MAX_TOKENS.get(section_name, 2000)
    try:
        prompt = load_prompt(template_name, **context)
        if user_instruction:
            prompt += f"\n\nAdditional user instruction: {user_instruction}"
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text
        return {"section": section_name, "content": text, "status": "success"}
    except Exception as e:
        logger.error(f"Failed to generate section '{section_name}': {e}")
        return {
            "section": section_name,
            "content": f"[Section could not be generated: {e}]",
            "status": "error",
        }


_SECTION_LABELS = {
    "bio": "Background and Analyst Bio",
    "earnings": "Post-Earnings Feedback and Questions",
    "peer": "Recent Peer Research",
    "forecast": "Analyst Forecast",
    "valuation": "Valuation Ratios",
}


async def edit_section(section_name: str, current_content: str, instruction: str) -> dict:
    """Edit an existing section by applying user instruction to current content.

    Used for draft-only regeneration (re_search=false) — modifies existing
    content instead of regenerating from scratch.

    Returns:
        {"section": section_name, "content": str, "status": "success"/"error"}
    """
    label = _SECTION_LABELS.get(section_name, section_name)
    max_tokens = _SECTION_MAX_TOKENS.get(section_name, 2000)

    if section_name == "earnings":
        prompt = (
            f"Here is the current content of the \"{label}\" section of an IR briefing memo:\n\n"
            f"---\n{current_content}\n---\n\n"
            f"The user wants the following change:\n{instruction}\n\n"
            f"IMPORTANT: The user may provide information that is NOT in the original transcript "
            f"(e.g., from private meetings, off-the-record conversations, or their own knowledge). "
            f"You MUST incorporate this information exactly as described. Add it as a clearly "
            f"labeled note at the end of the section, formatted as:\n\n"
            f"**Note:** [user-provided information]\n\n"
            f"Keep ALL existing content intact. Only ADD or MODIFY what the user specifically requests. "
            f"Return the full updated section — not just the changes. "
            f"Maintain the same markdown formatting and professional IR tone."
        )
    else:
        prompt = (
            f"Here is the current content of the \"{label}\" section of an IR briefing memo:\n\n"
            f"---\n{current_content}\n---\n\n"
            f"The user wants the following change:\n{instruction}\n\n"
            f"Modify the existing content to incorporate this change. Keep all existing content "
            f"intact unless the user specifically asks to remove or replace something. "
            f"Return the full updated section — not just the changes. "
            f"Maintain the same markdown formatting and professional IR tone."
        )

    try:
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text
        return {"section": section_name, "content": text, "status": "success"}
    except Exception as e:
        logger.error(f"Failed to edit section '{section_name}': {e}")
        return {
            "section": section_name,
            "content": current_content,  # preserve original on failure
            "status": "error",
        }


async def edit_forecast_table(table_rows: list[dict], instruction: str) -> list[dict] | None:
    """Edit a forecast table by sending its JSON structure + user instruction to Claude.

    Claude returns a modified JSON array.  Each row has:
        {label, indent, analyst, consensus, delta, bold?, highlight?}

    Returns the parsed list on success, or None on failure.
    """
    rows_json = json.dumps(table_rows, indent=2, default=str)

    prompt = (
        "Here is the current forecast table as a JSON array. Each row has:\n"
        "  label (metric name), indent (0=parent, 1=sub, 2=sub-sub),\n"
        "  analyst (number or null), consensus (number or null), delta (string like \"+3.2%\" or null).\n\n"
        f"```json\n{rows_json}\n```\n\n"
        f"The user wants: {instruction}\n\n"
        "Return ONLY a modified JSON array with the same structure.\n"
        "Rules:\n"
        "- You may add rows, remove rows, or reorder rows.\n"
        "- For new rows, calculate values from existing rows if possible (e.g. a subtotal is the sum of its children). "
        "If a value cannot be computed, use null.\n"
        "- For calculated values, compute the delta as: (analyst - consensus) / consensus * 100, "
        "formatted as \"+X.X%\" or \"-X.X%\". If consensus is 0 or null, set delta to null.\n"
        "- Preserve the indent field to maintain the hierarchy.\n"
        "- To bold a row, add \"bold\": true.\n"
        "- To highlight a row, add \"highlight\": true.\n"
        "- Do NOT wrap the output in markdown code fences. Return raw JSON only."
    )

    try:
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text.strip()

        # Strip markdown code fences if Claude added them anyway
        if text.startswith("```"):
            import re as _re
            match = _re.search(r"```(?:json)?\s*\n(.*?)\n```", text, _re.DOTALL)
            if match:
                text = match.group(1)

        result = json.loads(text)
        if isinstance(result, list):
            return result
        logger.error("edit_forecast_table: Claude returned non-list JSON")
        return None
    except Exception as e:
        logger.error(f"Failed to edit forecast table: {e}")
        return None


async def run_quality_check(sections: dict, metadata: dict) -> dict:
    """Run quality check on all memo sections.

    Returns:
        {"overall_status": "pass"/"warnings"/"fail", "sections": {...}, "summary": str}
    """
    try:
        prompt = load_prompt("quality_check", all_sections=json.dumps(sections, indent=2, default=str), **metadata)
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text

        # Try to parse JSON from the response
        # Claude may wrap JSON in markdown code blocks
        json_match = text
        if "```" in text:
            import re
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
            if match:
                json_match = match.group(1)

        try:
            result = json.loads(json_match)
            return result
        except json.JSONDecodeError:
            return {
                "overall_status": "warnings",
                "sections": {},
                "summary": text[:500],
            }
    except Exception as e:
        logger.error(f"Quality check failed: {e}")
        return {
            "overall_status": "error",
            "sections": {},
            "summary": f"Quality check could not be completed: {e}",
        }
