# TripWeaver

An AI‑assisted trip planning app that researches your destination, finds flight and stay options, generates diverse activities, and streams progress live to the UI while the plan is being built.

## Why TripWeaver
- Streamed progress so users aren’t stuck waiting on a spinner
- Fewer, smarter upstream API calls to reduce cost and latency
- Parallel execution where safe (flights, stays, activities), with sequential synthesis (budget, itinerary)
- Human‑readable logs and structured outputs for easy integration

---

## Architecture overview

- Frontend: React + TypeScript (in `frontend/`)
  - Connects to a streaming endpoint (SSE) to show live planning progress
  - Renders the final plan (flights, stays, activities, day‑by‑day itinerary)

- Backend: FastAPI (in `backend/app/`)
  - Orchestrates a set of “agents” that each produce part of the trip
  - Two execution modes:
    - Sequential graph builder (default)
    - Parallel “fast” executor (optional), running independent agents concurrently
  - Integrations
    - Tavily (search, map, crawl/extract)
    - OpenAI (structured generation)
    - Google Places (venue data; guarded by API key)
  - Streaming: Server‑Sent Events (SSE) streaming of progress messages

- Infra & Dev
  - Docker Compose for containerized runs
  - Python virtual environment for local backend

---

## User flow

1) User enters trip details (origin, destination, dates, hobbies).
2) Frontend calls the backend streaming endpoint `GET /plan-trip/stream`.
3) Backend runs the pipeline step‑by‑step and emits progress events:
   - Destination Research → Flights → Stays → Activities → Budget → Itinerary
4) Frontend shows live updates from these events.
5) When complete, backend emits a final `result` event with the full plan.
6) Frontend renders flights, stays, an activities catalog, and a day‑by‑day itinerary.

---

## Backend

### Key files
- `backend/app/api.py` — FastAPI app, routes, and streaming generator
- `backend/app/graph/agents.py` — Canonical agents for research, flights, stays, activities, budget, itinerary
- `backend/app/graph/build_graph.py` —
  - `build_graph()` returns the sequential graph (default)
  - `build_graph_fast()` returns a parallel executor with an `.invoke(state)` signature
- `backend/app/integrations/` — clients for Tavily, OpenAI, Google Places
- `backend/measure_latency.py` — end‑to‑end latency measurement script

### API endpoints
- `POST /plan-trip` — Synchronous planning
  - Body: JSON TripRequest
  - Response: TripResponse `{ plan, logs, success, message }`

- `POST /plan-trip/stream` and `GET /plan-trip/stream` — Streaming (SSE)
  - Emits `data: {"stage": ..., ...}\n\n` lines as the pipeline advances
  - Stages include: Destination Research, Flights Found/Refined, Stays Found/Refined, Activities Generated/Deduplicated, Budget Estimated, Itinerary Synthesized, complete, result

- `GET /health` — Health check

### Models (simplified)
- TravelerPrefs: origin, destination, start_date, end_date, adults, budget_level, hobbies[], trip_type, constraints{}
- Plan: flights[], stays[], activities_catalog[], itinerary[DayPlan], activities_budget, sources{}

### Environment variables
Create `backend/.env` (or export in your shell):
- `OPENAI_API_KEY` — required for activity generation/refinement
- `TAVILY_API_KEY` — required for search/map/extract
- `GOOGLE_PLACES_API_KEY` — required for Google Places venue lookups (optional but recommended)

Optional toggles:
- Fast/parallel mode is available via `build_graph_fast()` in code. If you want to enable it globally, change the graph construction in `app/api.py`:
  - Replace `graph = build_graph()` with `graph = build_graph_fast()`

### Run backend locally (Windows PowerShell)
Prereqs: Python 3.10+ (3.13 supported), pip

1) Create & activate a virtualenv (optional if using the provided `trip_env/`):
   - Create: `python -m venv trip_env`
   - Activate: `./trip_env/Scripts/Activate.ps1`

2) Install backend deps:
   - `pip install -r backend/requirements.txt`

3) Set environment variables (PowerShell):
   - `$env:OPENAI_API_KEY = "..."`
   - `$env:TAVILY_API_KEY = "..."`
   - `$env:GOOGLE_PLACES_API_KEY = "..."`

4) Start the server (auto‑reload):
   - `python backend/run_server.py`
   - App serves at http://localhost:8000

5) Test streaming quickly:
   - Open http://localhost:8000/health in a browser
   - Use the frontend (below) or a tool that supports SSE to view progress

### Docker Compose
If you prefer containers:
- Ensure `.env` contains the required API keys.
- Run Docker Desktop.
- From repo root: `docker compose up --build`

---

## Frontend

The frontend consumes SSE events to show real‑time planning progress and renders the final plan when ready.

Key points:
- Connects to `GET /plan-trip/stream` using `EventSource`
- Handles stages like `Flights Found`, `Stays Refined`, `Activities Generated`, etc.
- Renders flights, stays, and a day‑by‑day itinerary once `result` arrives.

Typical local run (adapt if package manager differs):
1) From `frontend/`:
   - `npm install` (or `pnpm install`, or `yarn`)
   - `npm run dev` (or equivalent) to start the dev server
2) Configure the backend base URL if the frontend expects a specific env var (often in `.env` or a config file)

SSE usage snippet (in React/TS):
```ts
useEffect(() => {
  const params = new URLSearchParams({
    origin, destination, start_date, end_date,
    hobbies: JSON.stringify(hobbies),
  });
  const es = new EventSource(`${API_BASE}/plan-trip/stream?${params.toString()}`);

  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    switch (data.stage) {
      case 'start':
      case 'Destination Research':
      case 'Flights Found':
      case 'Stays Found':
      case 'Activities Generated':
      case 'Budget Estimated':
      case 'Itinerary Synthesized':
        // append to progress log
        break;
      case 'result':
        // render data.result.plan
        break;
      case 'complete':
      default:
        break;
    }
  };
  es.onerror = () => es.close();
  return () => es.close();
}, [origin, destination, start_date, end_date, hobbies]);
```

---

## Performance & cost

- Reduced Tavily calls through batched queries and skipping heavy crawl steps unless valuable
- Activities generated using Google Places + OpenAI (with seeded fallback), avoiding many small searches
- Parallel execution (optional) runs flights, stays, and activities concurrently
- Streaming UX communicates progress early to reduce perceived latency

For benchmarking, use `backend/measure_latency.py` to time the end‑to‑end flow.

---

## Security & secrets
- Do not commit API keys
- Prefer `.env` (backend) or platform secret stores
- The Google Places client enforces an API key guard and only initializes if available

---

## Testing & troubleshooting

- Backend smoke:
  - `python backend/run_server.py` and open http://localhost:8000/health
  - POST to `/plan-trip` with a minimal body
- Streaming issues:
  - Ensure CORS headers allow your frontend origin (currently `*` for dev)
  - Check proxies/CDN that may buffer SSE; headers set `X-Accel-Buffering: no`
- Windows PowerShell quoting:
  - For environment variables: `$env:KEY="value"`
  - For SSE testing, prefer the frontend or a dedicated SSE client

---

## Roadmap
- Add caching (destination + hobby set) to cut repeated calls
- Add unit/integration tests and load tests for  concurrent requests
- Add structured telemetry for stage timings
- Optional: feature flag to toggle sequential vs fast execution at runtime

---

## License
TBD

---

## Deploying the MVP (AWS + MongoDB Atlas)

This section outlines a pragmatic way to share the MVP quickly with real users.

### 1) Backend on AWS Elastic Beanstalk

- Create an Elastic Beanstalk Python application (Web Server environment).
- Configure environment variables in EB (Configuration → Software):
  - `OPENAI_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_PLACES_API_KEY`
  - `MONGODB_URI` (from MongoDB Atlas), `MONGODB_DB` (e.g. `tripweaver`)
- Scale settings: enable multi‑instance (min 2) if you expect traffic; use a load balanced environment.
- Health check path: `/health`.
- Build artifact: zip the `backend/` folder with a minimal Procfile if desired (uvicorn via run_server.py works for dev; for prod, consider a Gunicorn + Uvicorn worker).

Optional Procfile example:
```
web: python run_server.py
```

### 2) MongoDB Atlas setup

- Create a free/shared cluster.
- Create a database user and network access rule for your EB environment (or 0.0.0.0/0 for quick MVP only; tighten later).
- Get the connection string and store it in EB as `MONGODB_URI`.
- Our backend logs requests/results best‑effort via `app/integrations/mongo_client.py`.
  - No Mongo installed? Logging no‑ops safely.

### 3) CI/CD with GitHub Actions

- Create a workflow that:
  - Installs backend deps
  - Runs basic checks (lint/tests if present)
  - Packages the backend and deploys to EB (use AWS credentials stored as GitHub secrets)

High‑level steps:
- On push to main: build → test → deploy EB application version → update environment.

### 4) Frontend ↔ Backend ↔ MongoDB Atlas connectivity

- Frontend makes SSE GET calls to `https://<your-eb-domain>/plan-trip/stream?...`.
- CORS: Ensure EB environment sets appropriate CORS headers (we allow `*` for MVP in `api.py`).
- Backend connects to Mongo Atlas using `MONGODB_URI`.

### 5) Testing checklists

- Correctness: verify that the final `result` event includes non‑empty plan structures for a typical query (e.g., NBO → Dubai).
- Error handling: upstream key missing → Activities/Places gracefully falls back; API responds with error events; server stays healthy.
- Data logging: after a plan run, confirm a document exists in `trip_requests` with status and summary fields.

### 6) Minimal smoke tests (manual)

- Health: `GET /health` returns `{ status: "healthy" }`.
- Streaming: Start a plan and see progressive stages; final `result` emitted.
- Latency: run `python backend/measure_latency.py` locally to get baseline.
