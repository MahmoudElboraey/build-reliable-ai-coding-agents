# Architecture Decision Records (ADRs)

## ADR-001: Orchestrator = Claude Sonnet (NOT Python state machine)

**Decision:** Orchestrator is an LLM agent using claude-sonnet-4-6. User explicitly chose this.  
**Reason:** Stronger reasoning model for state evaluation, AC generation, and worker delegation decisions.  
**Consequence:** More flexible than pure state machine. Sonnet used only for orchestration, not for research or scoring (cost control).

## ADR-002: QA Agent = Claude Haiku (NOT Pydantic)

**Decision:** QA validation is an LLM agent using claude-haiku-4-5-20251001. User explicitly chose this.  
**Reason:** Keeps the agent architecture consistent and simple. Haiku is cheap enough for validation tasks.  
**Consequence:** Additional LLM call per agent output. QA Agent must return structured pass/fail JSON itself.

## ADR-003: Structured Output via tool_use

**Decision:** Both Research and Scoring agents return structured JSON via Claude `tool_use` (force tool call), not free-text with regex extraction.  
**Reason:** Regex on LLM output breaks under edge cases (extra prose, unicode, truncation).  
**Consequence:** Output schema enforced at API level. Pydantic parses the result.

## ADR-004: Tavily Pre-fetch Pattern

**Decision:** Research Agent flow = (1) Python calls Tavily, (2) injects results as context into Claude prompt.  
**Reason:** Simpler than giving Claude a search tool. Avoids tool_use loop complexity for search.  
**Consequence:** Search results are static per invocation. Sufficient for interview prep use case.

## ADR-005: SSE for Score Streaming

**Decision:** Use Server-Sent Events for scoring progress.  
**Reason:** 5 sequential scoring calls (each 5-15s) = 25-75s total. Silent UI is unusable.  
**Consequence:** FE receives per-question scores as they complete. FastAPI natively supports SSE via `StreamingResponse`.

## ADR-006: Single-user Local Deployment

**Decision:** No auth, single SQLite file, localhost only.  
**Reason:** Tool is for individual interview prep, not SaaS.  
**Consequence:** No user isolation needed. DB path = `./shaghalny.db`.

## ADR-007: FAILED State Recovery

**Decision:** Add `retry_count INTEGER DEFAULT 0` to sessions. `POST /sessions/{id}/retry` resets state to last valid checkpoint.  
**Reason:** PRD left FAILED as a dead end. Users need recovery path.  
**Consequence:** Max 3 retries before session locked. Prevents infinite loops on broken inputs.

## ADR-008: security-audit-engineer subagent tool grant fix

**Decision:** Added `Bash, Glob, Grep, Write` to the `security-audit-engineer` subagent's `tools:` frontmatter (was: `Agent, ListMcpResourcesTool, Read, ReadMcpResourceTool, TaskCreate, TaskGet, TaskList, TaskStop, TaskUpdate, WebFetch, WebSearch`).  
**Reason:** The agent's own methodology (SAST secret-grepping, Phase 16 tool execution — semgrep/gitleaks/trivy/npm audit/curl/testssl, persistent agent-memory writes) required tools it wasn't granted. It silently degraded to manual-review-only with no error.  
**Consequence:** Agent can now actually execute its documented methodology. Open follow-up: Phase 16 still has no authorization gate before running active network tools (`zap-baseline.py`, `testssl.sh`) against a live target — needs a prompt patch before this agent is pointed at anything but local/owned targets. See [agent_authoring_lessons.md](agent_authoring_lessons.md).
