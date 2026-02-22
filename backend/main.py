import json
import os
import pandas as pd
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

from config import EXCEL_PATH, SECTION_IDS

app = FastAPI(title="IR Memo Agent")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for completed memos (keyed by memo_id)
memo_store: dict[str, dict] = {}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/analysts")
async def list_analysts():
    """Read unique analysts from the Excel file for the dropdown."""
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="Forecasts")
        analysts = []
        for _, row in df.drop_duplicates(subset=["Analyst"]).iterrows():
            analysts.append({
                "name": row["Analyst"],
                "firm": row["Firm"],
            })
        return analysts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read analyst data: {e}")


@app.get("/api/generate")
async def generate_memo(
    request: Request,
    analyst: str = Query(..., description="Analyst name"),
    company: str = Query(default="MS", description="Company ticker"),
    sections: str = Query(default="all", description="Comma-separated section IDs or 'all'"),
):
    """Generate a briefing memo via SSE stream."""
    from agents.orchestrator import run_orchestrator

    selected = SECTION_IDS if sections == "all" else [s.strip() for s in sections.split(",")]

    async def event_stream():
        async for event in run_orchestrator(analyst, company, selected, request, memo_store):
            yield event

    return EventSourceResponse(event_stream())


class RegenerateRequest(BaseModel):
    section: str
    analyst: str
    instruction: str = ""
    re_search: bool = False
    original_data: dict = {}
    memo_id: str = ""
    current_content: str = ""


@app.post("/api/regenerate")
async def regenerate_section(req: RegenerateRequest, request: Request):
    """Regenerate a single memo section via SSE stream."""
    from agents.orchestrator import run_regeneration

    async def event_stream():
        async for event in run_regeneration(
            section=req.section,
            analyst_name=req.analyst,
            instruction=req.instruction,
            re_search=req.re_search,
            original_data=req.original_data,
            memo_store=memo_store,
            memo_id=req.memo_id,
            current_content=req.current_content,
        ):
            yield event

    return EventSourceResponse(event_stream())


@app.get("/api/download/{memo_id}")
async def download_memo(memo_id: str):
    """Download the generated memo as a Word document."""
    from export.word_export import generate_word_doc

    memo_data = memo_store.get(memo_id)
    if not memo_data:
        raise HTTPException(status_code=404, detail="Memo not found")

    docx_buffer = generate_word_doc(memo_data)
    filename = f"IR_1Pager_{memo_data.get('analyst', 'memo')}_{memo_id}.docx"
    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
