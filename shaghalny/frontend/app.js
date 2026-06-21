const API = 'http://localhost:8000';

// ── State ──────────────────────────────────────────────────────────────────
let sessionId = null;
let questions  = [];

// ── Panel helpers ──────────────────────────────────────────────────────────
function showPanel(name) {
  ['input','interview','eval'].forEach(p => {
    document.getElementById(`panel-${p}`).classList.toggle('hidden', p !== name);
  });
}

function setLoading(on, msg = '') {
  document.getElementById('input-loading').classList.toggle('hidden', !on);
  document.getElementById('form-input').classList.toggle('hidden', on);
  if (msg) document.getElementById('loading-msg').textContent = msg;
}

// ── CV drag-and-drop ───────────────────────────────────────────────────────
const cvFile     = document.getElementById('cv-file');
const cvDropzone = document.getElementById('cv-dropzone');

cvFile.addEventListener('change', () => showCvChosen(cvFile.files[0]?.name));

cvDropzone.addEventListener('dragover', e => { e.preventDefault(); cvDropzone.classList.add('border-brand'); });
cvDropzone.addEventListener('dragleave', ()  => cvDropzone.classList.remove('border-brand'));
cvDropzone.addEventListener('drop', e => {
  e.preventDefault();
  cvDropzone.classList.remove('border-brand');
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    cvFile.files = dt.files;
    showCvChosen(file.name);
  }
});

function showCvChosen(name) {
  document.getElementById('cv-placeholder').classList.add('hidden');
  const el = document.getElementById('cv-chosen');
  el.textContent = `✓ ${name}`;
  el.classList.remove('hidden');
}

// ── Fetch with timeout ─────────────────────────────────────────────────────
function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  return fetch(url, { ...options, signal: ctrl.signal })
    .finally(() => clearTimeout(timer));
}

// ── Panel 1: Input form ────────────────────────────────────────────────────
document.getElementById('form-input').addEventListener('submit', async e => {
  e.preventDefault();

  const file    = cvFile.files[0];
  const jdText  = document.getElementById('jd-text').value.trim();
  const company = document.getElementById('company-name').value.trim();

  if (!file)              return alert('Please upload your CV.');
  if (file && file.size > 1000000) return alert('CV file too large. Max 1MB. Compress or paste as text.');
  if (jdText.length < 50) return alert('Job description too short (min 50 chars).');

  setLoading(true, 'Creating session…');

  try {
    // 1. Create session
    const fd = new FormData();
    fd.append('cv_file', file);
    fd.append('jd_text', jdText);
    fd.append('company_name', company);

    const res = await fetchWithTimeout(`${API}/sessions`, { method: 'POST', body: fd }, 30000);
    if (!res.ok) throw new Error(await res.text());
    const { session_id } = await res.json();
    sessionId = session_id;

    document.getElementById('session-badge').textContent = `session: ${sessionId.slice(0,8)}`;
    document.getElementById('session-badge').classList.remove('hidden');

    // 2. Generate questions
    setLoading(true, 'Researching your profile and generating questions… (may take 15–30s)');
    const genRes = await fetchWithTimeout(`${API}/sessions/${sessionId}/questions/generate`, { method: 'POST' }, 60000);
    if (!genRes.ok) {
      const err = await genRes.json();
      throw new Error(err.detail || 'Question generation failed');
    }

    // 3. Load questions
    const qRes = await fetchWithTimeout(`${API}/sessions/${sessionId}/questions`, {}, 15000);
    if (!qRes.ok) throw new Error('Failed to load questions');
    questions = await qRes.json();

    renderQuestions(questions);
    showPanel('interview');
    document.getElementById('session-id-display').textContent = sessionId.slice(0,8);

  } catch (err) {
    setLoading(false);
    alert(`Error: ${err.message}`);
  }
});

// ── Panel 2: Questions ─────────────────────────────────────────────────────
function renderQuestions(qs) {
  const container = document.getElementById('questions-container');
  container.innerHTML = '';

  qs.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-4';
    card.innerHTML = `
      <div class="flex items-start gap-3">
        <span class="shrink-0 w-8 h-8 rounded-full bg-brand flex items-center justify-center text-sm font-bold">${q.question_number}</span>
        <p class="text-slate-100 font-medium leading-relaxed">${escHtml(q.question_text)}</p>
      </div>

      <details class="group">
        <summary class="flex items-center gap-2 text-xs text-slate-500 hover:text-warning transition-colors select-none">
          <span class="group-open:hidden">▶</span>
          <span class="hidden group-open:inline">▼</span>
          Why this question?
        </summary>
        <p class="mt-2 text-xs text-slate-400 leading-relaxed pl-4 border-l border-slate-700">${escHtml(q.difficulty_rationale)}</p>
      </details>

      <textarea
        id="answer-${q.id}"
        data-question-id="${q.id}"
        class="answer-box w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-success resize-none"
        rows="6"
        placeholder="Write your answer here… Markdown supported."
      ></textarea>
    `;
    container.appendChild(card);
  });

  // Enable submit when all 5 filled
  const textareas = container.querySelectorAll('textarea');
  textareas.forEach(ta => ta.addEventListener('input', checkAnswersFilled));
}

function checkAnswersFilled() {
  const allFilled = questions.every(q => {
    const ta = document.getElementById(`answer-${q.id}`);
    return ta && ta.value.trim().length > 0;
  });
  document.getElementById('btn-submit-answers').disabled = !allFilled;
}

document.getElementById('btn-submit-answers').addEventListener('click', async () => {
  const answers = questions.map(q => ({
    question_id: q.id,
    user_answer: document.getElementById(`answer-${q.id}`).value.trim(),
  }));

  document.getElementById('btn-submit-answers').disabled = true;
  document.getElementById('btn-submit-answers').textContent = 'Submitting…';

  try {
    const res = await fetchWithTimeout(`${API}/sessions/${sessionId}/answers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answers }) }, 30000);
    if (!res.ok) throw new Error(await res.text());

    showPanel('eval');
    startScoreStream();

  } catch (err) {
    document.getElementById('btn-submit-answers').disabled = false;
    document.getElementById('btn-submit-answers').textContent = 'Submit All Answers';
    alert(`Error: ${err.message}`);
  }
});

// ── Panel 3: Evaluation + SSE ──────────────────────────────────────────────
function startScoreStream() {
  const container = document.getElementById('scores-container');

  // Render 5 placeholder cards
  questions.forEach(q => {
    const card = document.createElement('div');
    card.id = `score-card-${q.id}`;
    card.className = 'bg-slate-900 border border-slate-700 rounded-2xl p-5 slide-in';
    card.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <span class="w-8 h-8 rounded-full bg-score flex items-center justify-center text-sm font-bold">${q.question_number}</span>
          <p class="text-sm text-slate-300 font-medium line-clamp-2 max-w-xs">${escHtml(q.question_text.slice(0, 80))}…</p>
        </div>
        <div id="badge-${q.id}" class="score-pending text-2xl font-bold text-slate-600">—</div>
      </div>
      <div id="rubric-${q.id}" class="space-y-3 text-sm text-slate-400 italic">Evaluating…</div>
    `;
    container.appendChild(card);
  });

  const evtSource = new EventSource(`${API}/sessions/${sessionId}/score`);

  let stallTimer = setTimeout(() => {
    evtSource.close();
    showError('Scoring timed out — no response for 60 seconds. Use Retry below.');
  }, 60000);

  function resetStallTimer() {
    clearTimeout(stallTimer);
    stallTimer = setTimeout(() => {
      evtSource.close();
      showError('Scoring timed out — no response for 60 seconds. Use Retry below.');
    }, 60000);
  }

  evtSource.addEventListener('score', e => {
    resetStallTimer();
    const data = JSON.parse(e.data);
    renderScore(data);
  });

  evtSource.addEventListener('complete', e => {
    resetStallTimer();
    clearTimeout(stallTimer);
    evtSource.close();
    const { overall_average } = JSON.parse(e.data);
    document.getElementById('overall-score').textContent = overall_average;
    document.getElementById('overall-card').classList.remove('hidden');
  });

  evtSource.addEventListener('error', e => {
    clearTimeout(stallTimer);
    evtSource.close();
    let msg = 'Scoring pipeline failed.';
    try { msg = JSON.parse(e.data).error || msg; } catch {}
    showError(msg);
  });

  // Network-level SSE error (connection dropped)
  evtSource.onerror = () => {
    clearTimeout(stallTimer);
    evtSource.close();
    showError('Connection lost during scoring. Use Retry below.');
  };
}

function renderScore(data) {
  const badge  = document.getElementById(`badge-${data.question_id}`);
  const rubric = document.getElementById(`rubric-${data.question_id}`);
  if (!badge || !rubric) return;

  badge.classList.remove('score-pending');
  badge.textContent  = data.final_numeric_score;
  badge.className    = `text-2xl font-bold ${scoreColor(data.final_numeric_score)}`;

  rubric.className = 'space-y-4 text-sm';
  rubric.innerHTML = `
    ${scoreSection('Technical Accuracy', data.score_technical_accuracy, 'text-brand')}
    ${scoreSection('Completeness',        data.score_completeness,       'text-success')}
    ${scoreSection('Communication',       data.score_communication,      'text-warning')}
    ${scoreSection('Areas for Improvement', data.score_improvements,    'text-danger')}
  `;
}

function scoreSection(title, content, colorClass) {
  return `
    <div class="score-section">
      <h4 class="${colorClass}">${title}</h4>
      <p class="text-slate-300 leading-relaxed whitespace-pre-wrap">${escHtml(content)}</p>
    </div>
  `;
}

function scoreColor(score) {
  if (score >= 80) return 'text-success';
  if (score >= 60) return 'text-warning';
  return 'text-danger';
}

// ── Error + Retry ──────────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('error-card').classList.remove('hidden');
}

document.getElementById('btn-retry').addEventListener('click', async () => {
  document.getElementById('btn-retry').disabled = true;
  document.getElementById('btn-retry').textContent = 'Retrying…';
  try {
    const stateRes = await fetchWithTimeout(`${API}/sessions/${sessionId}`, {}, 10000);
    if (!stateRes.ok) {
      const err = await stateRes.json();
      throw new Error(err.detail || 'State check failed');
    }
    const { current_state } = await stateRes.json();
    if (current_state === 'ANSWERS_SUBMITTED') {
      document.getElementById('error-card').classList.add('hidden');
      document.getElementById('scores-container').innerHTML = '';
      document.getElementById('overall-card').classList.add('hidden');
      document.getElementById('btn-retry').disabled = false;
      document.getElementById('btn-retry').textContent = 'Retry';
      startScoreStream();
      return;
    } else if (current_state === 'FAILED') {
      const res = await fetchWithTimeout(`${API}/sessions/${sessionId}/retry`, { method: 'POST' }, 15000);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Retry failed');
      }
      const { reset_to_state } = await res.json();
      document.getElementById('error-card').classList.add('hidden');
      document.getElementById('scores-container').innerHTML = '';
      document.getElementById('overall-card').classList.add('hidden');
      if (reset_to_state === 'INIT') {
        sessionId = null;
        showPanel('input');
      } else {
        document.getElementById('btn-retry').disabled = false;
        document.getElementById('btn-retry').textContent = 'Retry';
        startScoreStream();
      }
    } else {
      document.getElementById('error-card').classList.add('hidden');
      alert(`Session in unexpected state: ${current_state}`);
      document.getElementById('btn-retry').disabled = false;
      document.getElementById('btn-retry').textContent = 'Retry';
    }
  } catch (err) {
    document.getElementById('btn-retry').disabled = false;
    document.getElementById('btn-retry').textContent = 'Retry';
    alert(`Retry failed: ${err.message}`);
  }
});

// ── Util ───────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
