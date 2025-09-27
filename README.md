# TripWeaver

An AI‑assisted trip planning app that researches your destination, finds flight and stay options, generates diverse activities, and streams progress live to the UI while the plan is being built.

## Why TripWeaver
- Streamed progress so users aren’t stuck waiting on a spinner
- Fewer, smarter upstream API calls to reduce cost and latency
- Parallel execution where safe (flights, stays, activities), with sequential synthesis (budget, itinerary)
- Human‑readable logs and structured outputs for easy integration

---

## Current deployment snapshot

As currently configured, the MVP is deployed as follows:
- Backend: AWS Elastic Beanstalk (Python + Uvicorn/FastAPI)
- Frontend: S3 Static Website Hosting (HTTP)
- Database: MongoDB Atlas

Notes:
- The frontend uses a CRA env var `REACT_APP_API_BASE` to call the backend. When hosting the frontend on S3 (HTTP‑only), point it to the EB HTTP URL to avoid mixed‑content.
- For production/HTTPS, enable TLS on the EB load balancer (ACM + 443 listener) and point the frontend to the HTTPS API domain (or host the frontend on a HTTPS CDN like Amplify/CloudFront).

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

## Frontend (React + CRA) — streaming hookup

The frontend connects to the backend’s streaming endpoint (SSE) and renders progressive updates and the final result.

### Configure API base
We use a CRA‑style environment variable in the frontend:
- `frontend/.env.development`
  - `REACT_APP_API_BASE=http://tripweaver-env.eba-ersmezej.us-east-1.elasticbeanstalk.com`
- `frontend/.env.production`
  - `REACT_APP_API_BASE=http://tripweaver-env.eba-ersmezej.us-east-1.elasticbeanstalk.com`

The code reads this via `src/utils/api.ts`, which builds absolute URLs for fetch/EventSource.

### Local run
1) From `frontend/`:
   - `npm install`
   - `npm start`
2) The app will call the deployed EB backend by default (from the `.env.*` above).
   - To use a local backend instead, set `REACT_APP_API_BASE=http://127.0.0.1:8000` in `.env.development` and restart `npm start`.

### SSE is used by default
`src/context/TripContext.tsx` opens an `EventSource(apiUrl('/plan-trip/stream?...'))` and dispatches progress stages (`Destination Research`, `Flights Found`, `Stays Refined`, `Activities Generated`, etc.). When the `result` stage arrives, the final plan is rendered.

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

Elastic Beanstalk Procfile:
```
web: sh -c "uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"
```
Ensure the Procfile is at the ZIP root of the backend bundle. Our GitHub Action zips only the contents of `backend/`, so the Procfile is at the correct root in the artifact.

If EB Events say “generated a Procfile”, it didn’t find yours; redeploy the correct artifact.

Tip — Going HTTPS later (recommended for production):
- Request a free ACM certificate for `api.yourdomain.com` (us‑east‑1)
- EB → Configuration → Load balancer: add HTTPS (443) listener and attach the cert
- Point DNS (Route 53) `api.yourdomain.com` to the EB load balancer
- Update the frontend `REACT_APP_API_BASE` to `https://api.yourdomain.com`

### 2) MongoDB Atlas setup

- Create a free/shared cluster.
- Create a database user and network access rule for your EB environment (or 0.0.0.0/0 for quick MVP only; tighten later).
- Get the connection string and store it in EB as `MONGODB_URI`.
- Our backend logs requests/results best‑effort via `app/integrations/mongo_client.py`.
  - No Mongo installed? Logging no‑ops safely.

### 3) CI/CD with GitHub Actions

This repo includes `.github/workflows/deploy-backend-eb.yml` which:
- Checks out code and sets working directory to `backend/`
- Installs Python deps and runs a smoke compile
- Zips only the backend contents to `backend.zip` (Procfile at ZIP root)
- Deploys the artifact to Elastic Beanstalk using environment/app/region secrets

### 4) Frontend on S3 Static Website Hosting (HTTP)

To host the SPA over HTTP (useful for quick demos without TLS):

1) Build the frontend locally
- From `frontend/`: `npm install` then `npm run build`

2) Create an S3 bucket (unique name)
- Enable “Static website hosting”
- Index document: `index.html`; Error document: `index.html` (SPA routing)

3) Make the site publicly readable (demo‑only)
- Apply a public bucket policy like:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

4) Upload the frontend build
- Upload the contents of `frontend/build/` to the bucket root
- Open the S3 Static Website Hosting endpoint URL (HTTP)

5) Point the frontend at the backend
- Set `frontend/.env.development` and `frontend/.env.production`:
  - `REACT_APP_API_BASE=http://<your-eb-env>.elasticbeanstalk.com` (HTTP)
- Rebuild the frontend after changing env values (CRA reads env at build time)

Important:
- S3 static website hosting is HTTP‑only. When using it, keep the backend URL on HTTP to avoid browser mixed‑content errors. For production, enable HTTPS on EB and host the frontend on a HTTPS origin with an HTTPS API base.

### 4) Frontend ↔ Backend ↔ MongoDB Atlas connectivity

- Frontend makes SSE GET calls to `https://<your-eb-domain>/plan-trip/stream?...`.
- CORS: Ensure EB environment sets appropriate CORS headers (we allow `*` for MVP in `api.py`).
- Backend connects to Mongo Atlas using `MONGODB_URI`.

### 5) Testing checklists

- Correctness: verify that the final `result` event includes non‑empty plan structures for a typical query (e.g., NBO → Dubai).
- Error handling: upstream key missing → Activities/Places gracefully falls back; API responds with error events; server stays healthy.
- Data logging: after a plan run, confirm a document exists in `trip_requests` with status and summary fields.

### 6) Minimal smoke tests (manual)

- Health: `GET /health` returns `{ "status": "healthy" }`.
- Streaming: `GET /plan-trip/stream?...` shows stages and emits a final `result`.
- POST: `POST /plan-trip` may require increasing the Load Balancer idle timeout in EB (180–300s) if requests take long; prefer streaming in the UI.

### 7) Common deployment gotchas
- EB Events “generated a Procfile”: your bundle didn’t include a root‑level Procfile; fix ZIP shape.
- 504 on long `POST /plan-trip`: increase ALB idle timeout and/or rely on SSE endpoint for the UI.
- Activities show “fallback/seeded” tags: set `GOOGLE_PLACES_API_KEY` in EB to enable venue‑based activities.
