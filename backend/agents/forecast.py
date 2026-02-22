"""Forecast agent: reads Analyst Key Metrics Excel and formats forecast table."""
import logging
from datetime import datetime, timedelta

import pandas as pd

from config import EXCEL_PATH

logger = logging.getLogger(__name__)

# Mapping from Excel columns to display labels, in the order they appear in the table.
# Each entry: (display_label, analyst_column, consensus_column, indent_level)
FORECAST_ROWS = [
    ("ISG Revenues", "ISG Revenues", "Consensus ISG", 0),
    ("Total S&T", "Total S&T", "Consensus S&T", 1),
    ("Equity", "Equity", "Consensus Equity", 2),
    ("Fixed Income", "Fixed Income", "Consensus FI", 2),
    ("Total BD", "Total BD", "Consensus BD", 1),
    ("Advisory", "Advisory", "Consensus Advisory", 2),
    ("Equity U/W", "Equity U/W", "Consensus Eq UW", 2),
    ("Debt U/W", "Debt U/W", "Consensus Debt UW", 2),
    ("WM Revenues", "WM Revenues", "Consensus WM", 0),
    ("IM Revenues", "IM Revenues", "Consensus IM", 0),
    ("Firmwide Revenues", "Firmwide Revenues", "Consensus Firmwide", 0),
    ("EPS", "EPS", "Consensus EPS", 0),
    ("ROE", "ROE", "Consensus ROE", 0),
    ("ROTCE", "ROTCE", "Consensus ROTCE", 0),
]


def _calc_delta(analyst_val, consensus_val) -> str | None:
    """Calculate Δ vs Consensus % = (Analyst - Consensus) / Consensus × 100."""
    if analyst_val is None or consensus_val is None:
        return None
    try:
        analyst_f = float(analyst_val)
        consensus_f = float(consensus_val)
        if consensus_f == 0:
            return None
        delta = (analyst_f - consensus_f) / consensus_f * 100
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta:.1f}%"
    except (ValueError, TypeError):
        return None


async def read_forecast_data(analyst_name: str) -> dict:
    """Read forecast data for a specific analyst from the Excel file.

    Returns:
        {
            "status": "success"/"error",
            "analyst_name": str,
            "firm": str,
            "date_updated": str,
            "is_stale": bool,
            "table_rows": [{"label", "indent", "analyst", "consensus", "delta"}, ...],
            "rating": str,
            "price_target": number or None,
        }
    """
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="Forecasts")
    except Exception as e:
        logger.error(f"Failed to read Excel: {e}")
        return {"status": "error", "error": f"Failed to read Excel file: {e}"}

    # Filter for the selected analyst (case-insensitive)
    mask = df["Analyst"].str.lower() == analyst_name.lower()
    analyst_rows = df[mask]

    if analyst_rows.empty:
        return {
            "status": "error",
            "error": f"Analyst '{analyst_name}' not found in Excel file",
        }

    # Select the most recent entry by Date Updated
    analyst_rows = analyst_rows.copy()
    analyst_rows["Date Updated"] = pd.to_datetime(analyst_rows["Date Updated"])
    row = analyst_rows.sort_values("Date Updated", ascending=False).iloc[0]

    date_updated = row["Date Updated"]
    date_str = date_updated.strftime("%B %d, %Y") if pd.notna(date_updated) else "[Date unavailable]"

    # Check staleness (>30 days)
    is_stale = False
    if pd.notna(date_updated):
        is_stale = (datetime.now() - date_updated.to_pydatetime().replace(tzinfo=None)) > timedelta(days=30)

    # Build table rows
    table_rows = []
    for label, analyst_col, consensus_col, indent in FORECAST_ROWS:
        analyst_val = row.get(analyst_col)
        consensus_val = row.get(consensus_col)

        # Handle NaN
        if pd.isna(analyst_val):
            analyst_val = None
        if pd.isna(consensus_val):
            consensus_val = None

        delta = _calc_delta(analyst_val, consensus_val)

        table_rows.append({
            "label": label,
            "indent": indent,
            "analyst": analyst_val,
            "consensus": consensus_val,
            "delta": delta if delta else "[Value unavailable]",
        })

    # Rating and Price Target
    rating = row.get("Rating", "")
    if pd.isna(rating) or rating == "":
        rating = "[Not available]"
    price_target = row.get("Price Target")
    if pd.isna(price_target):
        price_target = None

    return {
        "status": "success",
        "analyst_name": row["Analyst"],
        "firm": row["Firm"],
        "date_updated": date_str,
        "is_stale": is_stale,
        "table_rows": table_rows,
        "rating": str(rating),
        "price_target": price_target,
    }
