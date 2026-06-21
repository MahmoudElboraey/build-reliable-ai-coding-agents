import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

import database as db
from models import SessionResponse, QuestionOut, AnswersSubmission, RetryResponse
from utils.cv_parser import extract_cv_text

MAX_RETRIES = 3
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Shaghalny Interview Prep")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.init_db()
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")


# ── Sessions ──────────────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    cv_file: UploadFile = File(...),
    jd_text: str = Form(..., min_length=50),
    company_name: str = Form(default=""),
):
    cv_text = await extract_cv_text(cv_file)
    session_id = await db.create_session(
        cv_text=cv_text,
        jd_text=jd_text,
        company_name=company_name or None,
    )
    return SessionResponse(session_id=session_id, state="INIT")


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


# ── Question Generation ───────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/questions/generate", response_model=SessionResponse)
async def generate_questions(session_id: str):
    session = await _require_session(session_id)
    if session["current_state"] != "INIT":
        raise HTTPException(409, f"Expected INIT, got {session['current_state']}")

    # Import here to avoid circular imports at module load
    from agents.orchestrator import run_orchestrator
    await run_orchestrator(session_id)

    updated = await db.get_session(session_id)
    return SessionResponse(session_id=session_id, state=updated["current_state"])


@app.get("/sessions/{session_id}/questions", response_model=list[QuestionOut])
async def get_questions(session_id: str):
    await _require_session(session_id)
    questions = await db.get_questions(session_id)
    if not questions:
        raise HTTPException(404, "No questions found for this session")
    return questions


# ── Answer Submission ─────────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/answers", response_model=SessionResponse)
async def submit_answers(session_id: str, body: AnswersSubmission):
    session = await _require_session(session_id)
    if session["current_state"] != "QUESTIONS_GENERATED":
        raise HTTPException(409, f"Expected QUESTIONS_GENERATED, got {session['current_state']}")

    ids = [a.question_id for a in body.answers]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "Duplicate question_id in answers submission")

    await db.save_answers(session_id, [a.model_dump() for a in body.answers])
    await db.update_state(session_id, "ANSWERS_SUBMITTED")

    return SessionResponse(session_id=session_id, state="ANSWERS_SUBMITTED")


# ── Scoring SSE Stream ────────────────────────────────────────────────────────

@app.get("/sessions/{session_id}/score")
async def stream_scores(session_id: str):
    session = await _require_session(session_id)
    if session["current_state"] != "ANSWERS_SUBMITTED":
        raise HTTPException(409, f"Expected ANSWERS_SUBMITTED, got {session['current_state']}")

    return StreamingResponse(
        _scoring_stream(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _scoring_stream(session_id: str) -> AsyncGenerator[str, None]:
    from agents.orchestrator import run_scoring_pipeline

    scores_total = 0
    scores_sum = 0

    try:
        async for event in run_scoring_pipeline(session_id):
            if event["type"] == "score":
                scores_sum += event["data"].get("final_numeric_score", 0)
                scores_total += 1
                yield f"event: score\ndata: {json.dumps(event['data'])}\n\n"
            elif event["type"] == "error":
                yield f"event: error\ndata: {json.dumps(event['data'])}\n\n"
                return
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return

    overall = round(scores_sum / scores_total) if scores_total else 0
    yield f"event: complete\ndata: {json.dumps({'session_id': session_id, 'overall_average': overall})}\n\n"


# ── Retry ─────────────────────────────────────────────────────────────────────

@app.post("/sessions/{session_id}/retry", response_model=RetryResponse)
async def retry_session(session_id: str):
    session = await _require_session(session_id)
    if session["current_state"] != "FAILED":
        raise HTTPException(409, "Session is not in FAILED state")

    retry_count = await db.increment_retry(session_id)
    if retry_count >= MAX_RETRIES:
        raise HTTPException(409, "Max retries exceeded. Session locked.")

    await db.reset_session_to_state(session_id, "INIT")
    return RetryResponse(session_id=session_id, reset_to_state="INIT", retry_count=retry_count)


# ── Static Frontend ───────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _require_session(session_id: str) -> dict:
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session
