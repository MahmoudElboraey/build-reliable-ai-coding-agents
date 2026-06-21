# Sprint Plan

## Update Protocol

Update this tracker immediately whenever a task or ad-hoc piece of work closes out — flip status, add a one-line note in the relevant section. A `PostToolUse(TaskUpdate)` hook fires when a task flips to `completed` and reminds the active session to update this file plus `knowledge_base/`. See `.claude/settings.json` and [agent_authoring_lessons.md](agent_authoring_lessons.md#lesson-3).

## Sprint 0 — Foundation (Tasks #1–3)
**Goal:** Project skeleton, DB schema, all agent docs finalized.

| Task | Subject | Status |
|------|---------|--------|
| #1 | S0-1: Project structure + knowledge base init | ✅ Done |
| #2 | S0-2: schema.sql + aiosqlite DB layer | ⏳ Pending |
| #3 | S0-3: Updated agentic-workflow docs | ✅ Done |

**Definition of Done:** All files exist, DB schema tested with SQLite CLI, agent docs reviewed.

---

## Sprint 1 — Backend Core (Tasks #4–5)
**Goal:** Working FastAPI server with all endpoints stubbed and PDF parsing live.

| Task | Subject | Status |
|------|---------|--------|
| #4 | S1-1: FastAPI skeleton + endpoint contracts | ⏳ Pending |
| #5 | S1-2: PDF + text CV parser utility | ⏳ Pending |

**Definition of Done:** `uvicorn main:app` starts. POST /sessions creates DB row. PDF upload extracts text.

---

## Sprint 2 — Agent Layer: Research (Tasks #6–8)
**Goal:** Full research pipeline working end-to-end. Input CV+JD → 5 questions in DB.

| Task | Subject | Status |
|------|---------|--------|
| #6 | S2-1: Orchestrator Agent (Sonnet) | ⏳ Pending |
| #7 | S2-2: Research Agent (Haiku + Tavily) | ⏳ Pending |
| #8 | S2-3: QA Agent (Haiku) | ⏳ Pending |

**Definition of Done:** POST /sessions/{id}/questions/generate returns 5 questions. QA passes. State = QUESTIONS_GENERATED.

---

## Sprint 3 — Agent Layer: Scoring (Tasks #9–10)
**Goal:** Full scoring pipeline. 5 answers submitted → SSE stream of scores → state = SCORED.

| Task | Subject | Status |
|------|---------|--------|
| #9 | S3-1: Scoring Agent (Haiku, iterative) | ⏳ Pending |
| #10 | S3-2: Answer submission + SSE streaming | ⏳ Pending |

**Definition of Done:** SSE stream emits 5 score events. All answers scored in DB. State = SCORED.

---

## Sprint 4 — Frontend (Tasks #11–13)
**Goal:** Full UI working against live backend. All 3 panels functional.

| Task | Subject | Status |
|------|---------|--------|
| #11 | S4-1: Input Panel | ⏳ Pending |
| #12 | S4-2: Interview Panel | ⏳ Pending |
| #13 | S4-3: Evaluation Panel + SSE consumer | ⏳ Pending |

**Definition of Done:** Full E2E flow in browser. Upload CV → See questions → Answer → See scores.

---

## Sprint 5 — Polish & Hardening (Tasks #14–15)
**Goal:** Error paths covered, setup is self-contained.

| Task | Subject | Status |
|------|---------|--------|
| #14 | S5-1: FAILED state recovery (retry endpoint + UI) | ⏳ Pending |
| #15 | S5-2: requirements.txt + .env.example + README | ⏳ Pending |

**Definition of Done:** Retry flow works in UI. Fresh install from README in < 5 minutes.

---

## Agent Infrastructure & Tooling (Outside Sprint Scope)

Ad-hoc work on `.claude/agents/` subagents, not tied to a numbered sprint task.

| Date | Item | Status |
|------|------|--------|
| 2026-06-20 | Created `security-audit-engineer` subagent (`.claude/agents/security-audit-engineer.md`) | ✅ Done |
| 2026-06-20 | Reviewed it — `tools:` frontmatter missing `Bash`/`Grep`/`Glob`/`Write` despite methodology requiring them (SAST grep, Phase 16 tool execution, memory writes). Fixed. | ✅ Done |
| 2026-06-20 | Open: Phase 16 active-scan tools (`zap-baseline.py`, `testssl.sh`) have no authorization-gate instruction now that `Bash` is granted | ⏳ Pending |
| 2026-06-20 | Configured `PostToolUse(TaskUpdate)` hook to remind session to update tracker + knowledge base on task completion | ✅ Done |

Details: [agent_authoring_lessons.md](agent_authoring_lessons.md), [architecture_decisions.md ADR-008](architecture_decisions.md#adr-008-security-audit-engineer-subagent-tool-grant-fix).

---

## Agent Model Assignments (Reference)

| Agent | Model | Purpose |
|-------|-------|---------|
| Orchestrator | claude-sonnet-4-6 | State evaluation, AC generation, delegation |
| Research Agent | claude-haiku-4-5-20251001 | Question generation with Tavily context |
| Scoring Agent | claude-haiku-4-5-20251001 | Per-question iterative evaluation |
| QA Agent | claude-haiku-4-5-20251001 | Output validation (Research + Scoring) |
