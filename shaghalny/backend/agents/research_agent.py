import asyncio
import anthropic
from duckduckgo_search import DDGS

_client = anthropic.AsyncAnthropic()

_QUESTIONS_TOOL = {
    "name": "output_questions",
    "description": "Output exactly 5 hard interview questions",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "question_number": {"type": "integer"},
                        "question_text": {"type": "string", "minLength": 50},
                        "difficulty_rationale": {"type": "string", "minLength": 30},
                    },
                    "required": ["question_number", "question_text", "difficulty_rationale"],
                },
            }
        },
        "required": ["questions"],
    },
}


async def run(session: dict) -> list[dict]:
    company = (session.get("company_name") or "").strip()
    cv_text = session["cv_text"]
    jd_text = session["jd_text"]

    try:
        search_context = await asyncio.wait_for(asyncio.to_thread(_search, company, jd_text), timeout=5.0) if company else ""
    except asyncio.TimeoutError:
        search_context = "Web search timed out."

    prompt = _build_prompt(cv_text, jd_text, company, search_context)

    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        tools=[_QUESTIONS_TOOL],
        tool_choice={"type": "tool", "name": "output_questions"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input["questions"]

    raise RuntimeError("Research agent returned no tool_use block")


def _search(company: str, jd_text: str) -> str:
    role_hint = jd_text[:200]
    query = f"{company} engineering interview questions technical"
    try:
        results = list(DDGS().text(query, max_results=3))
        if not results:
            return ""
        snippets = [f"- {r['title']}: {r['body'][:300]}" for r in results]
        return "Known interview patterns from web search:\n" + "\n".join(snippets)
    except Exception:
        return "Web search unavailable for this query."


def _build_prompt(cv_text: str, jd_text: str, company: str, search_context: str) -> str:
    company_section = f"Target Company: {company}\n{search_context}\n" if company else ""
    return f"""You are an expert technical recruiter and system architect. Generate exactly 5 brutally hard interview questions.

{company_section}
Candidate CV:
{cv_text}

Job Description:
{jd_text}

Instructions:
1. Identify gaps: skills/tools in JD that are absent or weak in CV
2. Target those gaps with deep conceptual or practical design scenarios
3. Calibrate difficulty to the seniority level in the JD
4. Each question must be specific — no generic "explain X" questions
5. difficulty_rationale must reference the exact CV gap or company pattern being tested

Call output_questions with your 5 questions."""
