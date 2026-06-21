# API Contracts

## Base URL: `http://localhost:8000`

---

### POST /sessions
Create new session.

**Request (multipart/form-data):**
- `cv_file`: File (PDF or txt)
- `jd_text`: string
- `company_name`: string (optional)

**Response 201:**
```json
{ "session_id": "uuid", "state": "INIT" }
```

---

### POST /sessions/{id}/questions/generate
Trigger Orchestrator → Research Agent → QA Agent pipeline.

**Response 202:**
```json
{ "session_id": "...", "state": "QUESTIONS_GENERATED" }
```
Blocks until questions written to DB (or FAILED).

---

### GET /sessions/{id}/questions
Fetch generated questions.

**Response 200:**
```json
[
  { "id": "...", "question_number": 1, "question_text": "...", "difficulty_rationale": "..." }
]
```

---

### POST /sessions/{id}/answers
Submit all 5 answers.

**Request (JSON):**
```json
[
  { "question_id": "...", "user_answer": "markdown text..." }
]
```
Must contain exactly 5 items.

**Response 202:**
```json
{ "session_id": "...", "state": "ANSWERS_SUBMITTED" }
```

---

### GET /sessions/{id}/score  ← SSE Stream
Triggers scoring pipeline. Returns Server-Sent Events.

**Event format (per question scored):**
```
event: score
data: {"question_id": "...", "question_number": 1, "score_technical_accuracy": "...", "score_completeness": "...", "score_communication": "...", "score_improvements": "...", "final_numeric_score": 75}
```

**Final event:**
```
event: complete
data: {"session_id": "...", "overall_average": 72}
```

**Error event:**
```
event: error
data: {"session_id": "...", "state": "FAILED", "error_detail": "..."}
```

---

### POST /sessions/{id}/retry
Reset FAILED session to last valid checkpoint.

**Response 200:**
```json
{ "session_id": "...", "reset_to_state": "INIT", "retry_count": 1 }
```

**Response 409** (if retry_count >= 3):
```json
{ "error": "Max retries exceeded. Session locked." }
```

---

### GET /sessions/{id}
Get full session state.

**Response 200:**
```json
{
  "id": "...",
  "state": "SCORED",
  "company_name": "...",
  "retry_count": 0,
  "updated_at": "..."
}
```
