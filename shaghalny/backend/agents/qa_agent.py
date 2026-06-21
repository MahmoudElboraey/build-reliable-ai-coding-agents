import json
import anthropic

_client = anthropic.AsyncAnthropic()

_VERDICT_TOOL = {
    "name": "qa_verdict",
    "description": "Return structured pass/fail verdict",
    "input_schema": {
        "type": "object",
        "properties": {
            "pass": {"type": "boolean"},
            "failed_checks": {"type": "array", "items": {"type": "string"}},
            "error_detail": {"type": ["string", "null"]},
        },
        "required": ["pass", "failed_checks", "error_detail"],
    },
}


async def validate_research(questions: list[dict]) -> dict:
    prompt = f"""You are a QA gatekeeper. Validate this research agent output.

Rules:
1. Must be a list of exactly 5 objects
2. Each must have: question_number, question_text, difficulty_rationale
3. question_text: min 50 chars, no placeholders (TODO, [INSERT, ...)
4. difficulty_rationale: must reference specific gap or company pattern, not generic

Output to validate:
{json.dumps(questions, indent=2)}

Call qa_verdict with your findings."""

    return await _call(prompt)


async def validate_scoring(score: dict) -> dict:
    prompt = f"""You are a QA gatekeeper. Validate this scoring agent output.

Rules:
1. Must be a JSON object
2. Must have all 4 fields: score_technical_accuracy, score_completeness, score_communication, score_improvements
3. All 4 fields: non-empty, min 30 chars
4. final_numeric_score: integer between 1 and 100
5. No truncated text (must not end mid-sentence)

Output to validate:
{json.dumps(score, indent=2)}

Call qa_verdict with your findings."""

    return await _call(prompt)


async def _call(prompt: str) -> dict:
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        tools=[_VERDICT_TOOL],
        tool_choice={"type": "tool", "name": "qa_verdict"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {"pass": False, "failed_checks": ["QA agent returned no tool_use block"], "error_detail": "Internal QA failure"}
