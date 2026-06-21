"""
Orchestrator uses claude-sonnet-4-6 to evaluate session state and decide next action.
Python handles all I/O; Sonnet handles reasoning and AC generation.
"""
import json
import anthropic

_VALID_ACTIONS = {"trigger_research", "trigger_scoring", "await_ui", "mark_failed", "mark_complete"}
from typing import AsyncGenerator

import database as db
from agents import research_agent, qa_agent, scoring_agent

_client = anthropic.AsyncAnthropic()

_ACTION_TOOL = {
    "name": "orchestrator_decision",
    "description": "Decide next orchestration action for this session",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["trigger_research", "trigger_scoring", "await_ui", "mark_failed", "mark_complete"],
            },
            "acceptance_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What must be true for this action to be considered successful",
            },
            "reasoning": {"type": "string"},
        },
        "required": ["action", "acceptance_criteria", "reasoning"],
    },
}


async def run_orchestrator(session_id: str) -> None:
    """Called by FastAPI to drive state transition."""
    session_meta = await db.get_session(session_id)

    if session_meta["current_state"] != "INIT":
        await db.update_state(session_id, "FAILED", f"run_orchestrator called with invalid state: {session_meta['current_state']}")
        return

    decision = await _decide(session_meta)

    if decision["action"] == "trigger_research":
        session_full = await db.get_session_full(session_id)
        try:
            questions = await research_agent.run(session_full)
        except Exception as e:
            await db.update_state(session_id, "FAILED", f"Research agent error: {e}")
            return

        try:
            qa_result = await qa_agent.validate_research(questions)
        except Exception as e:
            await db.update_state(session_id, "FAILED", f"QA agent error: {e}")
            return
        if not qa_result["pass"]:
            await db.update_state(session_id, "FAILED", qa_result["error_detail"])
            return

        await db.save_questions(session_id, questions)
        await db.update_state(session_id, "QUESTIONS_GENERATED")

    elif decision["action"] == "mark_failed":
        await db.update_state(session_id, "FAILED", decision["reasoning"])


async def run_scoring_pipeline(session_id: str) -> AsyncGenerator[dict, None]:
    """Async generator: yields {type, data} events for SSE stream."""
    questions = await db.get_questions(session_id)
    session_full = await db.get_session_full(session_id)
    jd_text = session_full["jd_text"]

    for q in questions:
        answer_row = await db.get_answer_for_question(session_id, q["id"])
        if not answer_row:
            yield {"type": "error", "data": {"error": f"No answer found for question {q['question_number']}"}}
            await db.update_state(session_id, "FAILED", "Missing answer during scoring")
            return

        try:
            score = await scoring_agent.run(
                jd_text=jd_text,
                question_text=q["question_text"],
                candidate_answer=answer_row["user_answer"],
            )
        except Exception as e:
            yield {"type": "error", "data": {"error": str(e)}}
            await db.update_state(session_id, "FAILED", f"Scoring agent error: {e}")
            return

        try:
            qa_result = await qa_agent.validate_scoring(score)
        except Exception as e:
            yield {"type": "error", "data": {"error": f"QA agent error: {e}"}}
            await db.update_state(session_id, "FAILED", f"QA agent error: {e}")
            return
        if not qa_result["pass"]:
            yield {"type": "error", "data": {"error": qa_result["error_detail"]}}
            await db.update_state(session_id, "FAILED", qa_result["error_detail"])
            return

        await db.save_score(
            session_id=session_id,
            question_id=q["id"],
            score_technical_accuracy=score["score_technical_accuracy"],
            score_completeness=score["score_completeness"],
            score_communication=score["score_communication"],
            score_improvements=score["score_improvements"],
            final_numeric_score=score["final_numeric_score"],
        )

        yield {
            "type": "score",
            "data": {
                "question_id": q["id"],
                "question_number": q["question_number"],
                **score,
            },
        }

    await db.update_state(session_id, "SCORED")


async def _decide(session_meta: dict) -> dict:
    state = session_meta["current_state"]
    prompt = f"""You are an interview prep system orchestrator. Evaluate the current session state and decide the next action.

Session metadata:
- state: {state}
- retry_count: {session_meta['retry_count']}
- last_error: {session_meta.get('last_error')}

State machine rules:
- INIT → trigger_research
- QUESTIONS_GENERATED → await_ui (waiting for user to answer questions)
- ANSWERS_SUBMITTED → trigger_scoring
- SCORED → mark_complete
- FAILED → mark_failed

Call orchestrator_decision with your action and acceptance criteria for that action."""

    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        tools=[_ACTION_TOOL],
        tool_choice={"type": "tool", "name": "orchestrator_decision"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            decision = block.input
            if decision.get("action") not in _VALID_ACTIONS:
                return {"action": "mark_failed", "acceptance_criteria": [], "reasoning": f"Orchestrator returned invalid action: {decision.get('action')}"}
            return decision

    return {"action": "mark_failed", "acceptance_criteria": [], "reasoning": "Orchestrator returned no decision"}
