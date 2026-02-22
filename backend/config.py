import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Financial Modeling Prep API (free tier: 250 calls/day)
# Sign up at https://financialmodelingprep.com/ for a free key
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

# SEC EDGAR requires identification in User-Agent header
SEC_EDGAR_USER_AGENT = "IR-Memo-Agent research@example.com"

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
EXCEL_PATH = DATA_DIR / "analyst_key_metrics.xlsx"
TRANSCRIPT_PATH = DATA_DIR / "ms_transcript.txt"

# Demo scenario defaults
DEFAULT_COMPANY = "Morgan Stanley"
DEFAULT_TICKER = "MS"
PEER_TICKERS = ["GS", "JPM", "BAC", "C", "WFC", "SCHW"]
ALL_TICKERS = [DEFAULT_TICKER] + PEER_TICKERS

# CIK lookup (SEC EDGAR identifier)
COMPANY_CIKS = {
    "MS": "0000895421",
}

# Section IDs
SECTION_IDS = ["bio", "forecast", "earnings", "peer", "valuation"]
