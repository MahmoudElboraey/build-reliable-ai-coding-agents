# Handover Demo — Multi-Agent Workflow with File-Based State

Toy pipeline showing the pattern for **long-running, multi-agent processes that survive closing the session**. Same idea as `agentic-workflow/` in the repo root (Orchestrator → Worker → QA), but state lives in a plain JSON file instead of the SQLite DB — so any Claude Code session, even a brand new one with zero memory, can pick the process back up just by reading `state.json`.

## Why a file instead of a DB

The real app's state machine (`INIT → QUESTIONS_GENERATED → ...`) needs a running FastAPI server + DB. This pattern needs nothing running — `state.json` on disk *is* the process. Close the terminal, reopen tomorrow, point Claude at the file, it resumes exactly where it left off.

## Pieces

```
handover-demo/
├── state.json          # single source of truth: status, current_stage, history, artifacts
├── stages/              # one prompt-spec per agent, mirrors agentic-workflow/ style
│   ├── 1_planner.md
│   ├── 2_builder.md
│   ├── 3_reviewer.md
│   └── 4_finalizer.md
└── artifacts/           # outputs each stage produces, referenced from state.json
```

## The contract

Every stage agent gets the **same three jobs**, no exceptions:
1. Read `state.json` + whatever `artifacts.*` path it needs.
2. Do its narrow task, write output to `artifacts/`.
3. **Update `state.json` itself** — mark its own `stages[i]`, append one `history[]` entry, set `current_stage` to the next stage, bump `updated_at`. Only the finalizer is allowed to flip top-level `status` to `COMPLETED`. Any stage can flip it to `FAILED` (see retry rule in each spec).

Because the agent that does the work is also the one that writes the handover, there's no separate "orchestrator writes state" step to forget.

## How a session resumes

State.json's own `resume_instructions` field carries the resume algorithm — it doesn't live in your head or in this README alone, so it survives a `/clear` too:

1. Find the first entry in `stages[]` with `status != "done"`.
2. Spawn the agent in `stages/<that-name>.md`, pass it `process_id` + the `state.json` path.
3. Repeat until `current_stage == "done"` and `status == "COMPLETED"`.

To resume after closing a session, just tell Claude:
> "Resume the workflow at `examples/handover-demo/state.json`."

Claude reads the file, sees `current_stage`, spawns the matching agent — no re-explaining what already happened, because `history[]` + `artifacts/` already hold it.

## Failure / retry

`retry_count` + `max_retries` live at the top level. A failing stage increments `retry_count` and either re-points `current_stage` at the stage to redo (see `3_reviewer.md` — it can kick back to `builder`) or, past the limit, leaves `status: "FAILED"` parked for a human to look at. Nothing auto-loops forever.

## Run it yourself

This was executed live as a demo — check `state.json.history[]` and `artifacts/FINAL_REPORT.md` for the actual run. To re-run from scratch, reset `state.json` to the pending template (see git history / this file's first version) and ask Claude to start the workflow.

## Adapting this to a real long process

Swap the toy poem stages for whatever your real pipeline needs (scrape → transform → validate → publish, codegen → test → fix → ship, etc). Keep three things fixed: one `state.json`, one prompt-spec per stage under `stages/`, and the rule that **the stage agent updates its own state before handing off**.
