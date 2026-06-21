# Agent Authoring Lessons

Generalizable lessons from building/reviewing `.claude/agents/*.md` subagents — apply these when writing or editing any agent in this repo (orchestrator, research, scoring, QA, security-audit-engineer, future ones).

## Lesson 1: `tools:` frontmatter must match what the system prompt instructs the agent to do

Cross-check every tool the system prompt tells the agent to use (grep, run shell commands, write memory files, etc.) against the `tools:` frontmatter list. A mismatch doesn't error loudly — the agent silently degrades to a weaker fallback path (e.g. "automated tooling unavailable") and nobody notices unless they read the prompt line by line.

Found in: `security-audit-engineer.md` — `tools:` had only `Agent, ListMcpResourcesTool, Read, ReadMcpResourceTool, TaskCreate, TaskGet, TaskList, TaskStop, TaskUpdate, WebFetch, WebSearch`, but the methodology (SAST grep, Phase 16 tool execution, persistent-memory `Write`) required `Bash`/`Grep`/`Glob`/`Write`. Fixed by adding them. See [architecture_decisions.md ADR-008](architecture_decisions.md#adr-008-security-audit-engineer-subagent-tool-grant-fix).

## Lesson 2: active/offensive tooling needs an explicit authorization gate in the prompt

Any agent prompt that tells the model to run network-reaching tools (`zap-baseline.py`, `testssl.sh`, `nmap`, etc.) against "the target" needs an explicit instruction to confirm the target is owned by the user / within an authorized engagement *before* running — once the agent actually has `Bash` to execute them. Granting `Bash` to an agent whose prompt was written before `Bash` existed can silently turn a "describe what to run" agent into a "just runs it against whatever target it's given" agent. Re-audit the prompt's safety language whenever tool grants change.

Status: identified in `security-audit-engineer.md` Phase 16 (`zap-baseline.py` / `testssl.sh`) — **not yet patched**. Add a gating line next pass.

## Lesson 3: tracker + knowledge base updates are hooked, not manual

A `PostToolUse(TaskUpdate)` hook fires when a task flips to `completed`, reminding the active session to update `knowledge_base/sprint_plan.md` and the relevant `knowledge_base/*.md` file in the same turn. Configured in `.claude/settings.json`. Soft reminders in docs don't survive context compaction reliably — the hook does, since the harness re-injects it every time the matching tool call fires.
