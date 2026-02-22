# IR Briefing Memo Agent

## What This Is
An agentic prototype that generates IR management briefing memos (IR 1-Pagers) for sell-side analyst meetings. The agent acts as an IR professional that prepares polished, accurate briefing documents for executive preparation. The demo scenario is preparing a Morgan Stanley CFO briefing for a meeting with Mike Mayo (Wells Fargo Securities).

## Tech Stack
- **Frontend:** React + Tailwind CSS (deploy to Vercel)
- **Backend:** Python FastAPI
- **LLM:** Claude API (anthropic SDK, use claude-sonnet-4-20250514)
- **Web search:** DuckDuckGo (ddgs library)
- **Market data:** Yahoo Finance (yfinance library)
- **SEC filings:** SEC EDGAR (requests library)
- **Excel reading:** pandas + openpyxl
- **Document export:** python-docx

## Architecture
- Backend exposes FastAPI endpoints that the React frontend calls
- Backend orchestrates agent steps sequentially and streams progress updates to frontend via SSE or websockets
- Each agent step (research, forecast, market data, transcript, drafting, quality check) is a separate module
- Claude API handles narrative generation and quality checking
- Frontend shows real-time step-by-step progress with visual stepper

## Demo Scenario
- Analyst: Mike Mayo, Managing Director, Wells Fargo Securities
- Company: Morgan Stanley (ticker: MS)
- Peer banks: GS, JPM, BAC, C, WFC, SCHW
- Meeting context: CFO meeting with Mayo at Barclays Financial Services Conference

## 5 Sections To Generate
1. **Background and Analyst Bio** - from DuckDuckGo web search. Output as structured bullets: name/title, firm, coverage universe, prior experience, known stance, recent commentary.
2. **[Analyst Name]'s [Quarter] Forecast (As of [Date])** - from mock Analyst Key Metrics Excel. Read with pandas. Extract verbatim. Calculate delta % only. Must use exact table hierarchy with indentation: ISG > Total S&T > Equity/FI, ISG > Total BD > Advisory/Eq UW/Debt UW, WM, IM, Firmwide, EPS, ROE, ROTCE. Include Rating and Price Target below table.
3. **[Quarter] Post-Earnings Feedback and Questions** - from SEC EDGAR earnings transcript. Extract verbatim analyst quotes and management responses. Must include a "Key Topics" subsection listing main themes.
4. **Recent Peer Research** - from DuckDuckGo web search. Must include: report/commentary title, publishing firm, analyst name, publication date, key viewpoints vs MS, 3-5 core takeaways. Summarize only the most recent one.
5. **Valuation Ratios (As of [Date/Time])** - from Yahoo Finance. Live market data for MS + 6 peers. Clean comparison table with peer median.

## Mock Data
- Create `backend/data/analyst_key_metrics.xlsx` with 3 analysts (Mike Mayo, Betsy Graseck, Brennan Hawken)
- Each row has: analyst forecast values by segment + consensus values + rating + price target
- See BRIEF.md Section 2 for exact column structure and sample data

## Output Style Rules
- The agent acts as an IR professional preparing polished, accurate "IR 1-Pagers"
- ONLY generate sections that are selected. Skip unselected sections entirely.
- Use clear, structured bullets and short paragraphs. No long prose blocks.
- Maintain a professional IR tone suitable for internal/executive preparation.
- Never invent information. If data is missing, use placeholder: "[Data not available in provided materials]"
- Each section must follow its exact output format as defined in BRIEF.md Section 4.

## Word Document Formatting
The .docx export must look like a professional IR deliverable:
- Page: US Letter, 1-inch margins
- Font: Arial or Calibri, 11pt body, 14pt title, 12pt section headers
- Title: Bold, centered. Format: "IR 1-Pager: [Analyst Name] ([Firm]) - Prepared [Date]"
- Section headers: Bold, left-aligned, with subtle bottom border or shading
- Body: Structured bullets and short paragraphs
- Tables: Clean borders, header row shaded, numbers right-aligned
- Footer: "Confidential - For Internal Use Only" and page number
- Target length: 1-2 pages max. Executive-ready, scannable in under 2 minutes.

## Critical Rules
- Always use REAL data from live APIs (DuckDuckGo, Yahoo Finance, SEC EDGAR) for Sections 1, 3, 4, 5
- Section 2 (Forecast Table) reads from the mock Excel file only
- Never fabricate financial data, analyst quotes, or bio information
- Forecast values must be extracted VERBATIM from the Excel. Never infer or transform. Only allowed calculation is delta %
- If any forecast value is missing, insert: "[Value unavailable]"
- If Excel has additional KPIs beyond the listed ones, append them in the same table format
- Display "Date Updated" from Excel in the section title
- All Yahoo Finance data must show "as of" timestamps
- Earnings transcript quotes must be verbatim from the actual transcript
- Post-Earnings section must always include "Key Topics" subsection
- Recent Peer Research: if multiple reports found, summarize only the most recent
- If a data source fails or returns nothing, show section-specific placeholder, never hallucinate
- Quality check must flag missing data and forecast data older than 30 days as stale

## UI Requirements
- Clean, professional design (this demos to senior management)
- Analyst selector dropdown (pre-populated with analysts from the Excel file)
- Section checkboxes (select which of the 5 sections to generate, default all selected)
- Visual progress stepper showing each agent step with live status (pending, running, complete, error)
- Formatted memo display with clear section headers matching the IR 1-Pager format
- Forecast table and valuation table rendered as properly formatted tables with indentation and alignment
- Download button for Word document export
- No clutter, no unnecessary features
