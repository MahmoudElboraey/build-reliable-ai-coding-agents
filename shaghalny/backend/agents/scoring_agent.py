import anthropic

_client = anthropic.AsyncAnthropic()

_SCORE_TOOL = {
    "name": "output_score",
    "description": "Output structured evaluation score for one answer",
    "input_schema": {
        "type": "object",
        "properties": {
            "score_technical_accuracy": {"type": "string", "minLength": 30},
            "score_completeness": {"type": "string", "minLength": 30},
            "score_communication": {"type": "string", "minLength": 30},
            "score_improvements": {"type": "string", "minLength": 30},
            "final_numeric_score": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": [
            "score_technical_accuracy",
            "score_completeness",
            "score_communication",
            "score_improvements",
            "final_numeric_score",
        ],
    },
}


async def run(jd_text: str, question_text: str, candidate_answer: str) -> dict:
    prompt = f"""You are a senior principal engineer and hiring bar-raiser. Evaluate this candidate answer critically.

Job Description (calibrate seniority expectations from this):
{jd_text[:2000]}

Question:
{question_text}

Candidate Answer:
{candidate_answer}

Evaluation instructions:
- score_technical_accuracy: Is the architecture, logic, or code valid? Catch hallucinations and hand-waving.
- score_completeness: Did they address ALL facets? Call out missing edge cases, failure modes, scalability.
- score_communication: Is it structured and clear (STAR, technical vocab)? Penalize rambling.
- score_improvements: Bulleted actionable steps — specific patterns, terms, or designs missing.
- final_numeric_score: Integer 1-100 based on all four categories combined. No leniency.

Call output_score with your evaluation."""

    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        tools=[_SCORE_TOOL],
        tool_choice={"type": "tool", "name": "output_score"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    raise RuntimeError("Scoring agent returned no tool_use block")
