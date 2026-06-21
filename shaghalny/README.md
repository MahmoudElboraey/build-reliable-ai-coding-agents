# Shaghalny — AI Interview Prep Tool

Generates the 5 hardest interview questions tailored to your CV + JD, scores your answers with structured rubric feedback.

---

## System Architecture

```mermaid
flowchart TD
    subgraph FE["Frontend (Vanilla JS + Tailwind)"]
        A[Input Panel\nCV · JD · Company] --> B[Interview Panel\n5 Questions + Answers]
        B --> C[Evaluation Panel\nSSE Score Stream]
    end

    subgraph BE["Backend (FastAPI)"]
        D[POST /sessions] --> E[(SQLite\nshaghalny.db)]
        F[POST /questions/generate]
        G[POST /answers]
        H[GET /score\nSSE Stream]
    end

    subgraph ORCH["Orchestrator · claude-sonnet-4-6"]
        I[Read state metadata\nGenerate AC\nDecide next action]
    end

    subgraph AGENTS["Worker Agents · claude-haiku-4-5-20251001"]
        J[Research Agent\nDuckDuckGo + Gap Analysis\n→ 5 Questions]
        K[Scoring Agent\n1 Q-A pair per call\n× 5 iterations]
        L[QA Agent\nValidate output structure\nbefore every DB write]
    end

    A -->|multipart/form-data| D
    D --> E
    F --> I
    I -->|trigger| J
    J -->|output| L
    L -->|pass| E
    L -->|fail| M[FAILED state]
    E -->|state=QUESTIONS_GENERATED| B
    B -->|POST answers| G
    G --> E
    H --> I
    I -->|trigger ×5| K
    K -->|output| L
    L -->|pass| E
    E -->|score event| C

    style ORCH fill:#3b82f6,color:#fff
    style J fill:#22c55e,color:#fff
    style K fill:#a855f7,color:#fff
    style L fill:#f97316,color:#fff
    style M fill:#ef4444,color:#fff
    style FE fill:#1e293b,color:#fff
    style BE fill:#0f172a,color:#fff
    style AGENTS fill:#0f172a,color:#fff
```

---

## State Machine

```mermaid
stateDiagram-v2
    [*] --> INIT : Session created
    INIT --> QUESTIONS_GENERATED : Research Agent ✓ QA Agent ✓
    INIT --> FAILED : Research Agent ✗ or QA Agent ✗
    QUESTIONS_GENERATED --> ANSWERS_SUBMITTED : User submits 5 answers
    ANSWERS_SUBMITTED --> SCORED : All 5 Scoring Agent ✓ QA Agent ✓
    ANSWERS_SUBMITTED --> FAILED : Scoring Agent ✗ or QA Agent ✗
    FAILED --> INIT : Retry (max 3)
    SCORED --> [*]
```

---

## How Claude Code Built This System

```mermaid
flowchart TD
    subgraph CC["Claude Code (Orchestrator)"]
        P[Read PRD\nRoast + Validate] --> Q[Plan Sprints\n15 Tasks · 5 Sprints]
        Q --> R[Delegate to\nSubagents]
        R --> S[Track via\nTaskCreate / TaskUpdate]
        S --> T[Write to\nKnowledge Base]
    end

    subgraph KB["knowledge_base/"]
        U[tech_stack.md]
        V[architecture_decisions.md]
        W[prd_validation.md]
        X[api_contracts.md]
        Y[sprint_plan.md]
    end

    subgraph SPRINTS["Build Sprints"]
        S0["Sprint 0 ✅\nProject structure · Schema · Agent docs"]
        S1["Sprint 1 ✅\nFastAPI skeleton · CV parser"]
        S2["Sprint 2 ✅\nOrchestrator · Research · QA · Scoring agents"]
        S3["Sprint 3 🔄\nAnswer wiring · SSE stream"]
        S4["Sprint 4 ⏳\nFrontend 3 panels"]
        S5["Sprint 5 ⏳\nRetry flow · README · Setup"]
    end

    CC --> KB
    CC --> SPRINTS
    S0 --> S1 --> S2 --> S3 --> S4 --> S5

    style CC fill:#3b82f6,color:#fff
    style S0 fill:#22c55e,color:#fff
    style S1 fill:#22c55e,color:#fff
    style S2 fill:#22c55e,color:#fff
    style S3 fill:#f97316,color:#fff
    style S4 fill:#475569,color:#fff
    style S5 fill:#475569,color:#fff
```

---

## Agent Model Assignment

| Agent | Model | Trigger |
|-------|-------|---------|
| Orchestrator | `claude-sonnet-4-6` | Every state transition |
| Research Agent | `claude-haiku-4-5-20251001` | INIT → QUESTIONS_GENERATED |
| Scoring Agent | `claude-haiku-4-5-20251001` | ANSWERS_SUBMITTED → SCORED (×5) |
| QA Agent | `claude-haiku-4-5-20251001` | After every worker agent output |

---

## Quick Start

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

cd backend
python3 -m pip install -r requirements.txt
uvicorn main:app --reload
# Open http://localhost:8000
```

---

## Project Structure

```
shaghalny/
├── .env.example
├── README.md
├── knowledge_base/          # Architecture decisions, ADRs, API contracts
├── agentic-workflow/        # Agent system prompt specs
│   ├── 1_orchestrator.md
│   ├── 2_research_agent.md
│   ├── 3_scoring_agent.md
│   └── 4_qa_agent.md
├── backend/
│   ├── main.py              # FastAPI app, all endpoints
│   ├── database.py          # Async SQLite helpers
│   ├── models.py            # Pydantic request/response models
│   ├── schema.sql           # DB schema
│   ├── requirements.txt
│   ├── agents/
│   │   ├── orchestrator.py  # Sonnet — state decisions
│   │   ├── research_agent.py # Haiku + DuckDuckGo
│   │   ├── scoring_agent.py  # Haiku — iterative scoring
│   │   └── qa_agent.py       # Haiku — output validation
│   └── utils/
│       └── cv_parser.py     # PDF + text extraction
└── frontend/
    ├── index.html
    ├── app.js
    └── style.css
```
