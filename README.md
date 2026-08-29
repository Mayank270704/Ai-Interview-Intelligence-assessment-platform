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
uvicorn app.main:app --reload
```

The frontend runs on port 3000 and the API runs on port 8000 by default.
