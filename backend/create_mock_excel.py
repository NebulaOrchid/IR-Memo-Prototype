"""One-time script to create the mock analyst_key_metrics.xlsx file."""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Q1 2026 consensus estimates (in $M except EPS which is $/share)
# Based on: Q4 2025 actuals — ISG $7.5B, WM $7.3B, Firmwide $16.2B, EPS $2.63
# Q1 is typically seasonally softer than Q4
consensus = {
    "Consensus ISG": 7050,
    "Consensus S&T": 4950,
    "Consensus Equity": 2750,
    "Consensus FI": 2200,
    "Consensus BD": 2100,
    "Consensus Advisory": 850,
    "Consensus Eq UW": 700,
    "Consensus Debt UW": 550,
    "Consensus WM": 7150,
    "Consensus IM": 1500,
    "Consensus Firmwide": 15700,
    "Consensus EPS": 2.50,
    "Consensus ROE": 16.8,
    "Consensus ROTCE": 20.5,
}

rows = [
    {
        "Analyst": "Mike Mayo",
        "Firm": "Wells Fargo Securities",
        "Date Updated": "2026-02-10",
        "ISG Revenues": 7200,
        "Total S&T": 5100,
        "Equity": 2850,
        "Fixed Income": 2250,
        "Total BD": 2100,
        "Advisory": 870,
        "Equity U/W": 720,
        "Debt U/W": 510,
        "WM Revenues": 7300,
        "IM Revenues": 1520,
        "Firmwide Revenues": 16020,
        "EPS": 2.58,
        "ROE": 17.2,
        "ROTCE": 21.0,
        "Rating": "Overweight",
        "Price Target": 190,
        **consensus,
    },
    {
        "Analyst": "Betsy Graseck",
        "Firm": "Morgan Stanley Research",
        "Date Updated": "2026-02-12",
        "ISG Revenues": 7350,
        "Total S&T": 5200,
        "Equity": 2900,
        "Fixed Income": 2300,
        "Total BD": 2150,
        "Advisory": 880,
        "Equity U/W": 710,
        "Debt U/W": 560,
        "WM Revenues": 7400,
        "IM Revenues": 1480,
        "Firmwide Revenues": 16230,
        "EPS": 2.65,
        "ROE": 17.5,
        "ROTCE": 21.4,
        "Rating": "",
        "Price Target": None,
        **consensus,
    },
    {
        "Analyst": "Brennan Hawken",
        "Firm": "BMO Capital Markets",
        "Date Updated": "2026-02-08",
        "ISG Revenues": 6900,
        "Total S&T": 4800,
        "Equity": 2650,
        "Fixed Income": 2150,
        "Total BD": 2100,
        "Advisory": 830,
        "Equity U/W": 710,
        "Debt U/W": 560,
        "WM Revenues": 7000,
        "IM Revenues": 1480,
        "Firmwide Revenues": 15380,
        "EPS": 2.42,
        "ROE": 16.2,
        "ROTCE": 19.8,
        "Rating": "Market Perform",
        "Price Target": 168,
        **consensus,
    },
]

df = pd.DataFrame(rows)
df["Date Updated"] = pd.to_datetime(df["Date Updated"])

output_path = DATA_DIR / "analyst_key_metrics.xlsx"
df.to_excel(output_path, sheet_name="Forecasts", index=False)
print(f"Created {output_path}")
print(f"Columns: {list(df.columns)}")
print(f"Rows: {len(df)}")
print(df.to_string())
