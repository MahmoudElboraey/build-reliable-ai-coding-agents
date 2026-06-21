# Tech Stack Decisions

## Locked Choices

| Layer | Choice | Reason |
|-------|--------|--------|
| LLM (Orchestrator) | Claude Sonnet 4.6 (`claude-sonnet-4-6`) | Reasoning + state decisions need stronger model |
| LLM (Agents) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Research, Scoring, QA — fast + cheap for structured tasks |
| Web Search | Tavily API | Purpose-built for LLM agents, clean results, free tier |
| Backend | FastAPI (Python) | Async, SSE streaming support, auto OpenAPI docs |
| Database | SQLite + aiosqlite | Local-only, zero ops, stateless agent pattern |
| PDF Parsing | pypdf | Pure Python, no system deps |
| Validation | Pydantic v2 | Schema enforcement replacing QA LLM agent |
| Frontend | Vanilla JS + HTML + Tailwind CDN | Zero build tooling per PRD |
| Deploy | Local only | Single user, no auth required |

## Claude API Usage Pattern

- Structured output via `tool_use` (not regex parsing)
- Model: `claude-haiku-4-5-20251001`
- Research Agent: uses `brave_search` tool or Tavily via HTTP before prompt
- Scoring Agent: returns JSON via tool_use schema

## Environment Variables Required

```
ANTHROPIC_API_KEY=
TAVILY_API_KEY=
```
