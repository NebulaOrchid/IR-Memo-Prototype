# IR Briefing Memo Agent - Prototype Brief

---

## Use Case Overview

**Use Case Name:** IR Management Briefing Memo Generation (Agentic Prototype)
**Business Unit/Team:** Investor Relations
**Current Process Owner:** IR Associates / IR VP
**Demo Scenario:** Preparing CFO for upcoming meeting with Mike Mayo (Managing Director, Wells Fargo Securities) who covers Morgan Stanley stock
**Build Tool:** Claude Code
**Frontend:** React (deployed to Vercel)
**Backend:** Python FastAPI + Claude API
**Data Sources:** DuckDuckGo Search, Yahoo Finance, SEC EDGAR (all live, real data), Mock Analyst Key Metrics Excel (uploaded file)

---

## 1. Workflow Definition

### 1.1 Current Manual Workflow (As-Is)

1. IR associate receives management meeting schedule (CEO/CFO meetings with external sell-side analysts)
2. For each meeting, manually look up analyst background by searching the web, internal contacts, and LinkedIn for name, title, firm, coverage universe, prior experience
3. Open the Analyst Key Metrics Excel tracker, filter for the relevant analyst, extract latest forecast data by segment (ISG Revenues, WM Revenues, IM Revenues), compare to consensus, calculate deltas
4. Locate the most recent quarterly review report, read through it, manually extract verbatim analyst quotes and identify recurring themes (NII, capital returns, expenses, etc.)
5. Search for recent peer research published by the analyst or their firm on competitors (GS, JPM, BAC, C, WFC, SCHW), read reports, extract key viewpoints
6. Pull latest valuation ratios from the Daily Price Changes email (P/E, P/B, dividend yield, ROE, ROTCE)
7. Compile all sections into the firm's 1-pager Word template
8. Review for accuracy
9. Send to Head of IR for sign-off
10. Distribute to executive ahead of the meeting

**Time per memo:** 1-2 hours
**Frequency:** 3-5 per week
**Annual time spent:** 300-500 hours/year

### 1.2 Proposed Agentic Workflow (Prototype)

1. User opens the app in browser
2. User selects analyst name from dropdown (e.g., Mike Mayo)
3. User selects which sections to generate (or "All Sections")
4. User clicks "Generate Briefing Memo"
5. Agent autonomously executes:
   - Step 1: Search the web for analyst bio, career history, coverage universe, recent public commentary
   - Step 2: Read the Analyst Key Metrics Excel, filter for selected analyst, extract forecast data verbatim, format into the standard table with analyst vs. consensus vs. delta
   - Step 3: Retrieve and read most recent MS earnings call transcript from SEC EDGAR, extract analyst questions and management responses
   - Step 4: Search for recent peer research and analyst commentary on competitor banks
   - Step 5: Pull live valuation data (P/E, P/B, dividend yield, market cap) from Yahoo Finance for MS and peer banks
   - Step 6: Generate each memo section using Claude API with section-specific prompts and guardrails
   - Step 7: Run quality check (flag missing data, stale dates, placeholder values)
   - Step 8: Assemble complete formatted memo
6. App displays the complete memo with all sections
7. User reviews
8. User downloads as formatted Word document

**Time per memo with agent:** 10-15 minutes (mostly review time)
**Estimated time savings:** 70-80% per memo

### 1.3 Data Sources

| Data Need | Source | Library | Live Data? |
|---|---|---|---|
| Analyst bio, career, commentary | DuckDuckGo Search | ddgs | Yes |
| Analyst forecast vs. consensus | Analyst Key Metrics Excel (mock) | pandas + openpyxl | No (mock file) |
| Earnings call transcript | SEC EDGAR | requests / sec-edgar-downloader | Yes |
| Peer research summaries | DuckDuckGo Search | ddgs | Yes |
| Stock price, P/E, P/B, yield, market cap | Yahoo Finance | yfinance | Yes |
| LLM orchestration and drafting | Claude API | anthropic | Yes |

---

## 2. Inputs & Outputs

### 2.1 User Interactions

- "Generate a full briefing memo for Mike Mayo ahead of CFO's meeting on Friday"
- "Generate only the Analyst Bio and Valuation Ratios sections"

### 2.2 Expected Output Deliverables

- In-app display: Complete briefing memo rendered in the React UI with all selected sections
- Word document (.docx): Formatted IR 1-Pager download

---

## 3. Output Format and Style Rules

The agent acts as an IR professional that prepares polished, accurate "IR 1-Pagers." All output must follow these rules:

1. **ONLY generate sections that are selected.** If a section is not selected, skip it entirely.
2. Use clear, structured bullets and short paragraphs.
3. Never invent information. Use only data retrieved from live sources or the mock Excel.
4. If a required piece of data is missing, include a placeholder: "[Data not available in provided materials]"
5. Maintain a professional IR tone suitable for internal/executive preparation.
6. The document title must follow the format: **"IR 1-Pager: [Analyst Name] ([Firm]) - Prepared [Date]"**

### Word Document Formatting Rules

The .docx export must look like a professional IR deliverable, not a chatbot dump:

- **Page:** US Letter, 1-inch margins
- **Font:** Arial or Calibri, 11pt body, 14pt title, 12pt section headers
- **Title:** Bold, centered at top of page
- **Section headers:** Bold, left-aligned, with a subtle bottom border or shading to visually separate sections
- **Body text:** Structured bullets and short paragraphs. No long prose blocks.
- **Tables:** Clean borders, header row shaded, consistent column alignment, numbers right-aligned
- **Footer:** "Confidential - For Internal Use Only" and page number
- **Overall feel:** Executive-ready, scannable in under 2 minutes, fits on 1-2 pages

---

## 4. Section Definitions

### Section 1: "Background and Analyst Bio"

**What the agent does:**
1. Searches DuckDuckGo for "[analyst name] [firm] analyst bio coverage"
2. Searches for recent interviews, published commentary, conference appearances
3. Claude API synthesizes results into structured bio

**Output format (structured bullets, exactly this order):**

```
## Background and Analyst Bio

• [Full Name], [Title], [Firm]
• Coverage universe: [list of companies/sectors covered]
• Prior experience: [Previous firms and roles, in reverse chronological order]
• Known for: [Notable stance, reputation, or key published views]
• Recent commentary: [Most recent public statement or notable call on MS or the banking sector]
```

Each bullet must be concise (1-2 sentences max). Professional tone. No filler language.

**Demo scenario (Mike Mayo):**
- Mike Mayo, Managing Director, Wells Fargo Securities
- Covers large-cap US banks: MS, GS, JPM, BAC, C, WFC
- 25+ years covering bank stocks, previously at Deutsche Bank, CLSA, Prudential, Credit Suisse
- Author of "Exile on Wall Street," known for bearish calls on bank management
- Agent pulls all of this live from web search

### Section 2: "[Analyst Name]'s [Quarter] Forecast (As of [Date])"

**What the agent does:**
1. Reads the Analyst Key Metrics Excel file using pandas
2. Filters for the selected analyst (e.g., Mike Mayo)
3. Selects the latest/most recent forecast entry for that analyst
4. Extracts all values verbatim from the file. Never infers, calculates, or transforms any source numbers.
5. Calculates delta: Δ vs Consensus % = (Analyst - Consensus) / Consensus × 100
6. Formats into the standard table structure

**Section title format:** "[Analyst Name]'s 3Q25E Forecast (As of [Date Updated from Excel])"

**Output format (exact table structure with indentation hierarchy):**

The table MUST follow this exact structure and hierarchy:
- Top-level revenue categories: ISG Revenues, WM Revenues, IM Revenues, Firmwide Revenues
- Indented subcategories under ISG: Total S&T (with Equity, Fixed Income under it), Total BD (with Advisory, Equity U/W, Debt U/W under it)
- Columns: Analyst, Consensus, Δ vs Consensus %
- Additional KPI rows: EPS, ROE, ROTCE
- Rating and Price Target displayed below the table as separate line items

```
## Mike Mayo's 3Q25E Forecast (As of July 18, 2025)

| 3Q25 Revenues ($MM)     | Analyst | Consensus | Δ vs Consensus % |
|--------------------------|---------|-----------|-------------------|
| ISG Revenues             | 6,200   | 6,250     | -0.8%             |
|   Total S&T              | 4,800   | 4,850     | -1.0%             |
|     Equity               | 2,600   | 2,650     | -1.9%             |
|     Fixed Income         | 2,200   | 2,200     | 0.0%              |
|   Total BD               | 1,400   | 1,400     | 0.0%              |
|     Advisory             | 700     | 720       | -2.8%             |
|     Equity U/W           | 400     | 380       | +5.3%             |
|     Debt U/W             | 300     | 300       | 0.0%              |
| WM Revenues              | 7,100   | 7,050     | +0.7%             |
| IM Revenues              | 1,400   | 1,375     | +1.8%             |
| Firmwide Revenues        | 14,700  | 14,675    | +0.2%             |
| EPS                      | $2.05   | $2.08     | -1.4%             |
| ROE                      | 15.2%   | 15.3%     | -0.7%             |
| ROTCE                    | 18.1%   | 18.2%     | -0.5%             |

Rating: Overweight | Price Target: $125
```

**Data source:** Mock Excel file (`analyst_key_metrics.xlsx`) pre-loaded in the backend.

**Mock Excel structure (Sheet: "Forecasts"):**

Columns: Analyst, Firm, Date Updated, ISG Revenues, Total S&T, Equity, Fixed Income, Total BD, Advisory, Equity U/W, Debt U/W, WM Revenues, IM Revenues, Firmwide Revenues, EPS, ROE, ROTCE, Rating, Price Target, Consensus ISG, Consensus S&T, Consensus Equity, Consensus FI, Consensus BD, Consensus Advisory, Consensus Eq UW, Consensus Debt UW, Consensus WM, Consensus IM, Consensus Firmwide, Consensus EPS, Consensus ROE, Consensus ROTCE

Sample rows:
1. Mike Mayo | Wells Fargo | 2025-07-18 | 6200 | 4800 | 2600 | 2200 | 1400 | 700 | 400 | 300 | 7100 | 1400 | 14700 | 2.05 | 15.2 | 18.1 | Overweight | 125
2. Betsy Graseck | Morgan Stanley Research | 2025-07-20 | 6400 | 5000 | 2700 | 2300 | 1400 | 710 | 390 | 300 | 7300 | 1350 | 15050 | 2.15 | 15.8 | 18.9 | - | -
3. Brennan Hawken | UBS | 2025-07-15 | 6100 | 4700 | 2500 | 2200 | 1400 | 680 | 410 | 310 | 6900 | 1380 | 14380 | 1.98 | 14.9 | 17.6 | Neutral | 110

Consensus values (same for all rows): 6250 | 4850 | 2650 | 2200 | 1400 | 720 | 380 | 300 | 7050 | 1375 | 14675 | 2.08 | 15.3 | 18.2

**Guardrails:**
- Extract values verbatim from the Excel. Never infer or transform source numbers.
- The ONLY calculation allowed is: Δ vs Consensus % = (Analyst - Consensus) / Consensus × 100
- If any value is missing or not tied to the selected analyst, insert: "[Value unavailable]"
- Display the "Date Updated" from the Excel in the section title
- If the Excel includes additional KPIs for the analyst beyond what's listed, append them below in the same table format

### Section 3: "[Quarter] Post-Earnings Feedback and Questions"

**What the agent does:**
1. Searches SEC EDGAR for Morgan Stanley's most recent earnings call transcript
2. Identifies Mike Mayo's questions from the transcript (analysts identify themselves on earnings calls)
3. Extracts his exact questions and management's responses
4. Searches DuckDuckGo for Mayo's published post-earnings commentary on MS
5. Claude API identifies key themes across the quotes

**Output format (verbatim quotes followed by Key Topics subsection):**

```
## 2Q25 Post-Earnings Feedback and Questions

**Analyst Questions (from [Quarter] Earnings Call, [Date]):**

• "[Verbatim quote of Mayo's first question from transcript]"
  - Management response: [Brief summary of how CEO/CFO responded]

• "[Verbatim quote of Mayo's second question, if any]"
  - Management response: [Brief summary]

**Key Topics:**
[Short bullet list summarizing the main themes reflected in the quotes, e.g.:]
• Expense discipline and efficiency ratio trajectory
• Capital returns and buyback capacity post-CCAR
• Wealth Management net new asset growth sustainability
• ROTCE target progress
• ISG Markets revenue seasonality
```

**Guardrails:**
- Quotes must be verbatim from the earnings call transcript. Never paraphrase.
- If the analyst did not participate in the call, state: "[Analyst did not ask questions on this earnings call]"
- If quotes or topics are missing, insert: "[No quotes available]" or "[Topics unavailable]"
- Key Topics subsection is always included, summarizing the main themes

### Section 4: "Recent Peer Research"

**What the agent does:**
1. Searches DuckDuckGo for Mike Mayo's recent published commentary on MS peer banks (GS, JPM, BAC, C, WFC, SCHW)
2. Searches for recent sector-level calls (e.g., "large bank sector outlook")
3. Claude API summarizes the most recent and relevant findings

**Output format (structured with exact fields in this order):**

```
## Recent Peer Research

**Report/Commentary:** [Title or description of the most recent report or public commentary]
**Publishing Firm:** [Firm name]
**Analyst:** [Analyst name, if available]
**Date:** [Publication date, if available]

**Key Viewpoints vs. MS:**
• [How analyst's view on peers compares to their view on MS]

**Core Takeaways:**
• [Takeaway 1]
• [Takeaway 2]
• [Takeaway 3]
• [Takeaway 4, if available]
• [Takeaway 5, if available]
```

Must include 3-5 core takeaways. If multiple peer reports are found, summarize only the most recent one.

**Guardrails:**
- Only summarize content that is publicly accessible
- If no recent peer commentary found, output: "[No peer research available from public sources]"

### Section 5: "Valuation Ratios"

**What the agent does:**
1. Calls Yahoo Finance API for MS and peer bank tickers (GS, JPM, BAC, C, WFC, SCHW)
2. Pulls: current price, P/E, forward P/E, P/B, dividend yield, market cap, 52-week high/low
3. Calculates peer median for each metric
4. Formats into clean comparison table

**Output format (clean table, numbers right-aligned, header row shaded):**

```
## Valuation Ratios (As of [Date/Time])

| Metric          | MS     | GS     | JPM    | BAC    | C      | WFC    | SCHW   | Peer Median |
|-----------------|--------|--------|--------|--------|--------|--------|--------|-------------|
| Stock Price     | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX      |
| P/E (TTM)       | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx       |
| Forward P/E     | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx  | XX.Xx       |
| Price/Book      | X.Xx   | X.Xx   | X.Xx   | X.Xx   | X.Xx   | X.Xx   | X.Xx   | X.Xx        |
| Dividend Yield  | X.X%   | X.X%   | X.X%   | X.X%   | X.X%   | X.X%   | X.X%   | X.X%        |
| Market Cap ($B) | XXX.X  | XXX.X  | XXX.X  | XXX.X  | XXX.X  | XXX.X  | XXX.X  | XXX.X       |
| 52W High        | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | -           |
| 52W Low         | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | $XX.XX | -           |
```

Must include the "As of" timestamp in the section header. All values from Yahoo Finance are live.

**Guardrails:**
- Extract only the explicitly provided ratios and valuation metrics from Yahoo Finance
- Never calculate or infer missing items. If a metric is unavailable for a ticker, insert: "[N/A]"
- If valuation data is entirely unavailable, insert: "[Valuation data unavailable]"

---

## 5. Agentic Architecture

### Agent Orchestration Flow

```
User clicks "Generate Briefing Memo"
         |
         v
[Orchestrator] - Determines which sections are selected
         |
         ├──> [Research Agent] - Web search for analyst bio + peer research
         |         Uses: DuckDuckGo Search API
         |
         ├──> [Data Agent] - Reads Analyst Key Metrics Excel, pulls market data
         |         Uses: pandas, yfinance
         |
         ├──> [Transcript Agent] - Finds and parses earnings call transcript
         |         Uses: SEC EDGAR
         |
         └──> [Draft Agent] - Generates narrative for each section
                   Uses: Claude API with section-specific prompts
                            |
                            v
                   [Quality Check]
                   - Flags missing data
                   - Flags stale dates (e.g., Excel data older than 30 days)
                   - Flags placeholder values
                   - Reports confidence level per section
                            |
                            v
                   [Output]
                   - Renders memo in React UI
                   - Generates Word document via python-docx
                   - Provides download button
```

### Tool Functions

| Tool | Input | Output | Data Source |
|---|---|---|---|
| search_analyst_bio | analyst name, firm | Bio text, career history, coverage list | DuckDuckGo |
| search_analyst_commentary | analyst name, company | Recent quotes and viewpoints | DuckDuckGo |
| search_peer_research | analyst name, peer tickers | Research summaries and key calls | DuckDuckGo |
| read_forecast_excel | file path, analyst name | Filtered forecast row as structured data | pandas |
| format_forecast_table | analyst data, consensus data | Formatted table with delta calculations | Python |
| get_valuation_data | ticker list | Price, P/E, P/B, yield, market cap per ticker | Yahoo Finance |
| get_earnings_transcript | company ticker | Full transcript text | SEC EDGAR |
| extract_analyst_questions | transcript text, analyst name | Analyst questions + mgmt responses | Claude API parsing |
| generate_section | section name, context data | Formatted memo section text | Claude API |
| quality_check | all sections | Missing data flags, staleness warnings | Claude API |
| export_to_word | all sections | Formatted .docx file | python-docx |

---

## 6. Tech Stack

### Backend

| Component | Technology |
|---|---|
| API server | Python FastAPI |
| LLM orchestration | Claude API (anthropic SDK) |
| Web search | DuckDuckGo (ddgs) |
| Market data | Yahoo Finance (yfinance) |
| SEC filings | SEC EDGAR (requests) |
| Excel reading | pandas + openpyxl |
| Word export | python-docx |

### Frontend

| Component | Technology |
|---|---|
| Framework | React |
| Styling | Tailwind CSS |
| Key components | Analyst selector dropdown, section checkboxes, progress stepper with live status, memo display with formatted sections and tables, download button |
| Deployment | Vercel (free) |

### Project Structure

```
ir-memo-agent/
├── BRIEF.md                    (this file)
├── CLAUDE.md                   (Claude Code standing instructions)
├── backend/
│   ├── main.py                 (FastAPI server)
│   ├── requirements.txt
│   ├── agents/
│   │   ├── orchestrator.py     (chains all agents, manages flow)
│   │   ├── research.py         (DuckDuckGo search functions)
│   │   ├── market_data.py      (yfinance functions)
│   │   ├── sec_edgar.py        (earnings transcript retrieval + parsing)
│   │   ├── forecast.py         (Excel reading + forecast table formatting)
│   │   └── drafting.py         (Claude API calls for each section)
│   ├── prompts/
│   │   ├── analyst_bio.txt     (prompt template for Section 1)
│   │   ├── forecast_table.txt  (prompt template for Section 2)
│   │   ├── earnings_feedback.txt (prompt template for Section 3)
│   │   ├── peer_research.txt   (prompt template for Section 4)
│   │   └── quality_check.txt   (prompt template for QA step)
│   ├── data/
│   │   └── analyst_key_metrics.xlsx (mock Excel file)
│   └── export/
│       └── word_export.py      (python-docx formatting)
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── AnalystSelector.jsx
│   │   │   ├── SectionPicker.jsx
│   │   │   ├── ProgressStepper.jsx
│   │   │   ├── MemoDisplay.jsx
│   │   │   ├── ForecastTable.jsx
│   │   │   ├── ValuationTable.jsx
│   │   │   └── DownloadButton.jsx
│   │   └── api/
│   │       └── client.js       (API calls to backend)
│   └── tailwind.config.js
└── README.md
```

---

## 7. Demo Scenario Script

**Scenario:** It is Monday morning. The CFO of Morgan Stanley has a meeting with Mike Mayo (Wells Fargo Securities) at the Barclays Financial Services Conference on Friday. The IR team needs a briefing memo by Thursday EOD.

**Demo walkthrough:**

1. Open the app in browser
2. Select "Mike Mayo - Wells Fargo Securities" from analyst dropdown
3. Select "All Sections"
4. Click "Generate Briefing Memo"
5. Watch the agent execute steps in real-time with visual progress:
   - Searching web for Mike Mayo background... ✓
   - Reading Analyst Key Metrics Excel for Mayo's forecast... ✓
   - Calculating forecast vs. consensus deltas... ✓
   - Pulling MS earnings transcript from SEC EDGAR... ✓
   - Extracting Mayo's questions from transcript... ✓
   - Searching for Mayo's recent peer commentary... ✓
   - Pulling live valuation data for MS and 6 peers... ✓
   - Generating memo sections... ✓
   - Running quality check... ✓
   - Assembling Word document... ✓
6. Review the complete memo displayed in the app
7. Click "Download Word Document"
8. Open the .docx showing a professionally formatted IR 1-Pager

**Key demo talking points:**
- "The agent executed 10 steps autonomously. The IR associate clicked one button."
- "Bio, earnings transcript, and peer commentary are from live web and SEC data."
- "Valuation table has today's real market data, not static numbers."
- "Forecast table reads from the team's existing Excel tracker. No re-entry."
- "Quality check flagged that Mayo's forecast data was last updated 34 days ago, alerting IR to request fresh estimates."
- "Total time: under 2 minutes. Current manual process: 1-2 hours."
- "The Word document is formatted as a professional IR 1-Pager ready for executive review."

---

## 8. Estimated Build Effort

| Task | Time |
|---|---|
| Project setup (FastAPI + React scaffold) | 1 hour |
| Mock Excel file creation | 30 minutes |
| Tool functions (DuckDuckGo, yfinance, SEC EDGAR, pandas) | 3-4 hours |
| Claude API integration for section drafting | 2-3 hours |
| Forecast table reading and formatting | 1-2 hours |
| Quality check logic | 1 hour |
| React UI (selector, stepper, memo display, tables, download) | 3-4 hours |
| Word document export (professional IR formatting) | 2-3 hours |
| Section-specific prompt engineering | 2 hours |
| API wiring (frontend to backend) | 1-2 hours |
| Testing, polish, edge cases | 2-3 hours |
| Vercel deployment | 30 minutes |
| **Total** | **19-24 hours (weekend build)** |

---

## 9. Success Metrics

| Metric | Current Manual Process | Prototype |
|---|---|---|
| Time to generate one memo | 1-2 hours | Under 2 minutes |
| Human steps required | 10+ manual steps | 3 (select, click, review) |
| Data sources accessed manually | 5 separate sources | 1 (mock Excel pre-loaded, rest is live) |
| Output format | Manual Word formatting | Auto-generated professional IR 1-Pager |
| Data freshness | Depends on when IR last updated tracker | Real-time for 4 of 5 sections |
| Sections covered | 5/5 | 5/5 |

---

## 10. Guardrails and Accuracy Rules

1. **Only generate sections that are selected.** If a section is not selected, skip it entirely.
2. Use clear, structured bullets and short paragraphs. No long prose blocks.
3. Maintain a professional IR tone suitable for internal/executive preparation.
4. Never invent information. Use only data from live APIs or the mock Excel.
5. If a required piece of data is missing, include a placeholder: "[Data not available in provided materials]"
6. All financial data from Yahoo Finance must display the "as of" timestamp.
7. Forecast table values must be extracted verbatim from the Excel. The only calculation allowed is delta % = (Analyst - Consensus) / Consensus × 100.
8. If any forecast value is missing or not tied to the selected analyst, insert: "[Value unavailable]"
9. Forecast table must display the "Date Updated" from Excel in the section title so the user sees data freshness.
10. If the Excel includes additional KPIs for the analyst beyond those listed, append them below in the same table format.
11. Earnings transcript quotes must be verbatim. Never paraphrase or fabricate.
12. Post-Earnings section must always include a "Key Topics" subsection summarizing main themes.
13. Recent Peer Research must include: report/commentary title, publishing firm, analyst name (if available), publication date, key viewpoints vs. MS, and 3-5 core takeaways.
14. If multiple peer reports are found, summarize only the most recent one.
15. If a data source is unavailable or returns no results, display the section-specific placeholder message rather than fabricating content.
16. Quality check must flag any section where data could not be retrieved.
17. Quality check must flag forecast data older than 30 days as potentially stale.
18. Never present web search summaries as if they are proprietary research reports.
19. Word document must be formatted as a professional IR 1-Pager: structured bullets, clean tables, executive-ready tone, 1-2 pages max.
