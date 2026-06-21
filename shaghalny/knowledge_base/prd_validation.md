# PRD Validation Report

## Validated Good Patterns

- Stateless agents + SQLite as state bus — correct, prevents context bleed
- Iterative scoring (1 Q per LLM call) — correct, avoids 5x context overhead
- QA gatekeeper concept — correct instinct, wrong implementation (see fixes)

## Critical Issues Found & Fixes Applied

### ARCH-001: Orchestrator should NOT be an LLM
- **Problem:** PRD defines Orchestrator as an AI agent. Its job (read state, decide next step, trigger worker) is deterministic logic.
- **Fix:** Orchestrator = Python state machine. Zero tokens, zero hallucination risk, 100x faster.

### ARCH-002: QA Agent should NOT be an LLM  
- **Problem:** JSON validation via LLM is wasteful and introduces failure modes.
- **Fix:** Python `json.loads()` + Pydantic v2 schema validation. Cheaper, deterministic.

### ARCH-003: Score parsing via regex is fragile
- **Problem:** `FINAL_NUMERIC_SCORE: \d+` regex breaks when LLM adds prose around it.
- **Fix:** Scoring Agent returns structured JSON via Claude `tool_use`. No regex.

### ARCH-004: No API layer defined
- **Problem:** PRD has FE and DB but nothing connecting them.
- **Fix:** FastAPI with explicit endpoint contracts (see api_contracts.md).

### ARCH-005: No web search tool defined
- **Problem:** Research Agent told to "search web" with no mechanism.
- **Fix:** Tavily API — pre-fetch search results, inject into agent context.

### ARCH-006: No PDF parsing library
- **Problem:** CV upload mentioned but no extraction tech.
- **Fix:** pypdf for PDF, plain text fallback.

### ARCH-007: No streaming — UX will appear frozen
- **Problem:** 5 serial LLM scoring calls = potentially 2+ minutes of silence.
- **Fix:** Server-Sent Events (SSE) for score streaming per question.

### ARCH-008: Orchestrator "never ingest CV" but hands CV to Research Agent
- **Problem:** Contradiction in the PRD.
- **Fix:** Orchestrator reads CV from DB only to pass to Research Agent. "Never ingest for its own reasoning" is the real constraint.

### ARCH-009: No FAILED state recovery
- **Problem:** Session dies on FAILED, no retry path.
- **Fix:** Add `POST /sessions/{id}/retry` endpoint, reset state to previous valid state.

## Unchanged from PRD (validated correct)

- DB schema structure — solid
- 5-question output format
- Scoring rubric 4 headlines
- Session state machine: INIT → QUESTIONS_GENERATED → ANSWERS_SUBMITTED → SCORED
