# AI Interview Intelligence & Assessment Platform

Monorepo scaffold for an AI-assisted interview preparation and assessment platform.

## Layout

- `frontend`: Next.js and TypeScript application
- `backend`: FastAPI service and AI orchestration boundaries
- `ai-lab`: datasets, experiments, notebooks, and evaluation work
- `docs`: architecture and product documentation

## Local setup

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in DATABASE_URL, GEMINI_API_KEY, and the SUPABASE_* values
alembic upgrade head
uvicorn app.main:app --reload
```

The API will not start requests successfully without `DATABASE_URL`, and question
generation, answer analysis, and voice need `GEMINI_API_KEY`. See `backend/.env.example`
for what each setting is for. Never commit a filled-in `.env`.

The frontend runs on port 3000 and the API runs on port 8000 by default.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt   # runtime deps plus scikit-learn, used by the offline ML tests
python -m pytest -q
```

The suite is deterministic: Gemini, Supabase Auth, and Supabase Storage are all mocked.
The one live check that calls the real Gemini API is opt-in:

```powershell
$env:RUN_LIVE_LLM_TESTS = "1"; python -m pytest tests/ai/test_llm.py
```

## Offline ML experiments

`backend/app/ml` defines a training-data contract over the structured signals the
interview pipeline already produces, and `ai-lab/experiments/adaptive_interview`
trains an offline baseline on synthetic scenarios:

```powershell
python ai-lab/experiments/adaptive_interview/train_baseline.py
```

This is research scaffolding, not a product feature. No model runs in the
interview path, no API response is derived from one, and real interview turns
become training data only for candidates who explicitly opted in. See
`ai-lab/experiments/adaptive_interview/README.md` for the target, features,
metrics, and what the synthetic numbers do and do not mean.
