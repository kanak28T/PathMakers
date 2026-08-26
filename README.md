# PathMakers

AI-powered personalized learning roadmap — Hackathon project.

## Team structure

| Member | Owns |
|--------|------|
| K | `backend/` — FastAPI, Phase 3 graph engine, Phase 4 recalibrator |
| P | `data/`, `backend/phase1_profiler/`, `backend/phase2_matching/` |
| S | `ml/` — HistGradientBoosting training pipeline |
| R | `frontend/` — Next.js 14, React Flow canvas, XAI drawer |

## Quick start

### Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
# API available at http://localhost:8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
cp .env.local.example .env.local   # already set to localhost:8000
npm run dev
# App available at http://localhost:3000
```

The frontend builds entirely against the mock endpoints — no live backend needed for development.

## Contracts

All inter-phase data shapes are frozen in `contracts/schemas.py`. Do not change field names without a group sync.

## Frontend components

| Component | Purpose |
|-----------|---------|
| `RoadmapCanvas` | React Flow DAG canvas — fetches graph, renders nodes/edges, handles SSE patches |
| `CourseNode` | Custom node — status colour, lock overlay, SHAP fit score |
| `XAIDrawer` | Slide-in inspector — SHAP bar chart, skill tags, explanation text |
| `IntakeDrawer` | 4-step onboarding — role, skills, experience, weekly hours |
| `NodeActionBar` | Floating toolbar — mark complete / fail quiz / skip → fires RecalibrateRequest |
| `PatchToast` | SSE patch notification toast |

### Key hooks & utilities

- `hooks/useGraphPatch.ts` — SSE listener with auto-reconnect
- `lib/patchGraph.ts` — Pure diff merge (no full graph refetch on Phase 4 events)
- `lib/api.ts` — All backend calls with mock fallbacks
- `lib/types.ts` — TypeScript mirror of `contracts/schemas.py`
