# AI Interview Intelligence & Assessment Platform

An adaptive AI interview practice platform. A candidate uploads a resume, the
system extracts a structured candidate profile from it, and then conducts a live
interview in which **every question is generated at runtime** from the resume,
the conversation so far, and what the candidate has actually demonstrated. It is
not a question bank.

The interview runs the same intelligence pipeline in all three formats — text,
voice, and video. Only how the answer reaches the pipeline differs.

## The interview loop

Each turn runs the same cycle. Every stage is a separate component with its own
responsibility, and none of them decides another's job:

```
resume → candidate profile → opening question
   ↓
candidate answer
   ↓
Answer Intelligence   analyse the answer against the question and the profile
   ↓
Evaluation Engine     turn that analysis into evidence-based, confidence-weighted signals
   ↓
Knowledge State       accumulate what the candidate has demonstrated, and which
                      resume claims are now supported / unsupported / uncertain
   ↓
Interviewer Brain     decide the next action — DEEPEN, CLARIFY, CHALLENGE,
                      INVESTIGATE_CLAIM, CHANGE_TOPIC, raise/lower difficulty, …
   ↓
Question Engine       phrase exactly that decision as one natural question
   ↓
next question  →  (repeat)
```

`InterviewTurnService` (`backend/app/services/interview/turn_service.py`)
coordinates these and persists every turn, so an interview can be reconstructed
from the database alone. The service owns no interview reasoning of its own.

## Major components

| Area | Location | What it does |
| --- | --- | --- |
| Resume intelligence | `backend/app/ai/resume_intelligence/` | PDF text extraction, then a structured Gemini pass producing identity, education, skills, technologies, experience, projects, certifications, achievements, and **verifiable claims** |
| Answer intelligence | `backend/app/ai/answer_intelligence/` | Structured analysis of one answer: correctness, demonstrated/missing/incorrect concepts, reasoning quality, depth, unsupported claims |
| Evaluation engine | `backend/app/ai/evaluation_engine/` | Deterministic mapping of that analysis into evaluation signals plus an explicit confidence, treating missing evidence as uncertainty rather than as proof of ignorance |
| Knowledge State | `backend/app/ai/knowledge_intelligence/` | The accumulated per-concept picture of the candidate, and the verification status of each resume claim |
| Interviewer Brain | `backend/app/ai/interviewer_brain/` | Chooses the next interview action and target concept from the evidence, and tracks conversation state, explored concepts, and pending claims |
| Question engine | `backend/app/ai/question_engine/` | Turns a decision into one grounded question at the required difficulty; never invents candidate experience |
| Final assessment | `backend/app/ai/assessment/` | Scores are computed **deterministically** from the accumulated evaluation evidence; the LLM only phrases strengths, weaknesses, and the summary, with a deterministic fallback |
| ATS scoring | `backend/app/ai/ats/` | Fully deterministic resume scoring — readiness mode, or match against a job description. Makes no LLM call at all |
| World knowledge | `backend/app/ai/world_knowledge/` | Chunking, local hash embeddings, and ranked retrieval. The pipeline accepts retrieved knowledge on every turn; no route currently supplies any |
| Voice / video | `backend/app/ai/voice/`, `backend/app/api/v1/interviews.py` | Gemini speech-to-text and text-to-speech. Voice and video answers are transcribed and then run through the identical turn pipeline |
| Avatar | `frontend/src/components/avatar/`, `frontend/src/hooks/useAvatar.ts` | A stylised SVG interviewer driven purely by interview state, with mouth movement from the live amplitude of the question audio. No 3D asset, no avatar service, no paid API |
| ML foundation | `backend/app/ml/`, `ai-lab/` | Offline only — see below |

## Architecture

- **Backend**: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Supabase).
- **Frontend**: Next.js (App Router) and TypeScript.
- **Auth**: Supabase Auth (GoTrue) over REST. The backend never sees a password
  beyond forwarding one signup/login request, never issues or parses a JWT
  itself, and verifies every bearer token with Supabase.
- **Storage**: original resume PDFs go to a **private** Supabase Storage bucket
  under a server-generated `{candidate_id}/{resume_id}.pdf` path — never a
  client-supplied filename.
- **Ownership**: every candidate row records its owner. Resumes, interviews,
  turns, and assessments are reached only through their candidate, and a
  resource owned by someone else answers `404`, not `403`, so an id belonging to
  another user is indistinguishable from one that does not exist. Postgres RLS
  policies (migration `0006`) enforce the same rule as defence in depth.

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill it in
alembic upgrade head
uvicorn app.main:app --reload
```

The API logs the **names** of any missing required settings at startup (never
their values). Each one disables a specific step:

| Setting | Needed for |
| --- | --- |
| `DATABASE_URL` | everything that persists — candidates, resumes, interviews |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | signup, login, and bearer-token verification |
| `SUPABASE_SERVICE_ROLE_KEY` | writing the uploaded PDF to the private bucket. Resume upload answers `503` until it is set |
| `GEMINI_API_KEY` | resume extraction, question generation, answer analysis, voice |
| `GEMINI_MODEL` | must name a model your key can currently reach — a retired model name answers every request with `404` |

`CORS_ALLOW_ORIGINS` must be set explicitly in any deployment; the default only
covers local frontend development. Never commit a filled-in `.env`.

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local   # NEXT_PUBLIC_API_URL, default http://localhost:8000/api/v1
npm run dev
```

The frontend runs on port 3000 and the API on port 8000.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt   # runtime deps plus scikit-learn, for the offline ML tests
python -m pytest -q
```

```powershell
cd frontend
npm run typecheck
npm test
npm run build
```

The backend suite is deterministic: Gemini, Supabase Auth, and Supabase Storage
are mocked throughout. Two tests are conditional and skip unless you opt in:

```powershell
# Live Gemini call
$env:RUN_LIVE_LLM_TESTS = "1"; python -m pytest tests/ai/test_llm.py

# Persistence smoke test against a real PostgreSQL database.
# Never point this at a database holding real interview data.
$env:TEST_DATABASE_URL = "postgresql+psycopg2://..."; python -m pytest tests/db/test_persistence.py
```

## Offline ML foundation

`backend/app/ml` defines a training-data contract over the structured signals the
interview already produces, and `ai-lab/experiments/adaptive_interview` trains an
offline baseline predicting `InterviewDecision.difficulty_direction`:

```powershell
python ai-lab/experiments/adaptive_interview/train_baseline.py
```

This is research scaffolding, deliberately kept outside the product:

- No model runs in the interview path and no API response is derived from one.
  Difficulty is decided by the Interviewer Brain, exactly as before.
- The published metrics come from **synthetic** scenarios generated by
  `app/ml/synthetic.py`. They show the feature contract and training pipeline
  work end to end. They say nothing about real-world accuracy, which is
  currently unknown and unmeasured.
- Real interview turns become training data only via `--source consented`, which
  exports only turns whose candidate explicitly opted in (`app/ml/consent.py`).
  Consent defaults to off and is never inferred.

See `ai-lab/experiments/adaptive_interview/README.md` for the target, features,
and metrics.

## Known limitations

- **Latency.** Resume extraction and each interview turn are synchronous calls to
  Gemini. Extraction of a one-page resume typically takes tens of seconds, and
  longer when the model is under load. `GEMINI_TIMEOUT_SECONDS` bounds a single
  call, and transient upstream failures (`429`/`5xx`) are retried up to three
  times with backoff, but there is no background job queue: the client waits.
- **Video answers are transcribed, not watched.** The video flow extracts speech
  and runs it through the same pipeline. No emotion, engagement, or
  attentiveness signal is computed — `app/ai/video/provider.py` defines the
  extension point for that, and nothing implements it.
- **Rate limiting is per process.** `app/core/rate_limit.py` protects the
  credential endpoints within one worker. A multi-replica deployment must also
  rate-limit at the edge.
- **World-knowledge retrieval is not wired to a route.** The retrieval layer
  exists and is tested, and every pipeline entry point accepts retrieved
  knowledge, but no endpoint currently supplies any.
- **No interview history surface.** Results are reached by interview id; there is
  no "my past interviews" list.
