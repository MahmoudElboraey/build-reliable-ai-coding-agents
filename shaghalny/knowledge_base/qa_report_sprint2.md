# QA Report — Sprint 0–2 Delivery

**Date:** 2026-06-20  
**Reviewer:** cavecrew-reviewer agent  
**Scope:** schema.sql, database.py, main.py, models.py, cv_parser.py, orchestrator.py, research_agent.py, qa_agent.py, scoring_agent.py

## Findings

| # | File | Line | Severity | Problem | Fix |
|---|------|------|----------|---------|-----|
| 1 | database.py | 6 | 🔴 CRITICAL | Relative DB_PATH/SCHEMA_PATH breaks when uvicorn runs from non-backend dir | `Path(__file__).parent / "..."` |
| 2 | research_agent.py | 37 | 🔴 CRITICAL | `DDGS().text()` is sync, blocks FastAPI event loop | Wrap in `asyncio.to_thread()` |
| 3 | scoring_agent.py | 32 | 🟠 HIGH | `jd_text[:1000]` too short — truncates seniority/role info | Increase to 2000 chars |
| 4 | main.py | 140 | 🟡 MEDIUM | Retry gate `> MAX_RETRIES` allows 1 extra retry | Change to `>= MAX_RETRIES` |
| 5 | qa_agent.py | 30 | 🟡 MEDIUM | Passes Python list repr to LLM, not JSON string | Use `json.dumps(questions)` |
| 6 | orchestrator.py | 144 | 🟡 MEDIUM | No enum validation on Sonnet action — typo → silent `mark_failed` | Validate against VALID_ACTIONS set |
| 7 | cv_parser.py | 16 | 🟡 MEDIUM | No file type whitelist — .docx silently corrupts as UTF-8 | Reject unsupported types with HTTP 415 |
| 8 | database.py | 117 | 🟡 MEDIUM | `save_answers` FK violation gives cryptic aiosqlite error | Catch FK error, raise HTTP 400 |
| 9 | schema.sql | 9 | 🟡 MEDIUM | `updated_at` has no ON UPDATE trigger | Already handled explicitly in database.py — document invariant |
| 10 | main.py | 6 | 🟡 MEDIUM | Deferred agent imports inside functions — inconsistent pattern | Document reason (circular import avoidance) |
| 11 | research_agent.py | 65 | 🟡 MEDIUM | DDGS failure logged silently — prompt gets no signal search failed | Include "search unavailable" note in prompt |
| 12 | orchestrator.py | 51 | 🟡 MEDIUM | `validate_research(questions)` passes Python repr — duplicate of finding #5 | Fixed with json.dumps |

## Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 2 |
| 🟠 HIGH | 1 |
| 🟡 MEDIUM | 9 |

## Status
All findings fixed in same session. See git diff after Sprint 2 fixes commit.
