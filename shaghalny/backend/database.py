import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import aiosqlite

_HERE = Path(__file__).parent
DB_PATH = str(_HERE / "shaghalny.db")
SCHEMA_PATH = str(_HERE / "schema.sql")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        with open(SCHEMA_PATH) as f:
            await db.executescript(f.read())
        await db.commit()


# ── Sessions ──────────────────────────────────────────────────────────────────

async def create_session(cv_text: str, jd_text: str, company_name: Optional[str]) -> str:
    session_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, cv_text, jd_text, company_name) VALUES (?, ?, ?, ?)",
            (session_id, cv_text, jd_text, company_name),
        )
        await db.commit()
    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, company_name, current_state, retry_count, last_error, updated_at "
            "FROM sessions WHERE id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_session_full(session_id: str) -> Optional[dict]:
    """Includes cv_text and jd_text — only for agent payloads, never for routine orchestration."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_state(session_id: str, new_state: str, error: Optional[str] = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET current_state = ?, last_error = ?, updated_at = ? WHERE id = ?",
            (new_state, error, datetime.now(timezone.utc), session_id),
        )
        await db.commit()


async def increment_retry(session_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET retry_count = retry_count + 1, updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc), session_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT retry_count FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def reset_session_to_state(session_id: str, target_state: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET current_state = ?, last_error = NULL, updated_at = ? WHERE id = ?",
            (target_state, datetime.now(timezone.utc), session_id),
        )
        await db.commit()


# ── Questions ─────────────────────────────────────────────────────────────────

async def save_questions(session_id: str, questions: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for q in questions:
            await db.execute(
                "INSERT INTO questions (id, session_id, question_number, question_text, difficulty_rationale) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    session_id,
                    q["question_number"],
                    q["question_text"],
                    q["difficulty_rationale"],
                ),
            )
        await db.commit()


async def get_questions(session_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, question_number, question_text, difficulty_rationale "
            "FROM questions WHERE session_id = ? ORDER BY question_number",
            (session_id,),
        ) as cursor:
            return [dict(row) async for row in cursor]


# ── Answers ───────────────────────────────────────────────────────────────────

async def save_answers(session_id: str, answers: list[dict]) -> None:
    """answers: list of {question_id, user_answer}"""
    async with aiosqlite.connect(DB_PATH) as db:
        for a in answers:
            await db.execute(
                "INSERT INTO answers (id, session_id, question_id, user_answer) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), session_id, a["question_id"], a["user_answer"]),
            )
        await db.commit()


async def get_answer_for_question(session_id: str, question_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM answers WHERE session_id = ? AND question_id = ?",
            (session_id, question_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_score(
    session_id: str,
    question_id: str,
    score_technical_accuracy: str,
    score_completeness: str,
    score_communication: str,
    score_improvements: str,
    final_numeric_score: int,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE answers SET
                score_technical_accuracy = ?,
                score_completeness = ?,
                score_communication = ?,
                score_improvements = ?,
                final_numeric_score = ?
            WHERE session_id = ? AND question_id = ?""",
            (
                score_technical_accuracy,
                score_completeness,
                score_communication,
                score_improvements,
                final_numeric_score,
                session_id,
                question_id,
            ),
        )
        await db.commit()


async def get_scores(session_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT question_id, score_technical_accuracy, score_completeness, "
            "score_communication, score_improvements, final_numeric_score "
            "FROM answers WHERE session_id = ? ORDER BY rowid",
            (session_id,),
        ) as cursor:
            return [dict(row) async for row in cursor]
