# Prompt Manager System

Two-service architecture built for the ATS Week 1 internship project, extended
to use Postgres (per live instruction overriding the original SQLite spec)
and served behind nginx with a Vite + React frontend.

## Architecture

```
Browser --> nginx (port 80)
              |-- /            -> frontend/dist (React, static files)
              |-- /prompts/*   -> prompt-service (port 8000)
              `-- /reviews/*   -> review-service (port 8001)

prompt-service --owns--> Postgres (via SQLAlchemy)
review-service --calls--> prompt-service over HTTP (via httpx)
review-service --owns--> reviews/*.json (one file per review)
```

prompt-service and review-service are fully independent. review-service has
no database connection of its own and never imports anything from
prompt-service — it only knows prompt-service's HTTP API.

## Services

### prompt-service (port 8000)
- FastAPI + SQLAlchemy + Postgres
- Owns the `prompts` table exclusively
- Endpoints: `POST /prompts`, `GET /prompts`, `GET /prompts/{id}`,
  `PUT /prompts/{id}` (partial update supported), `DELETE /prompts/{id}`,
  `GET /prompts/{id}/exists`

### review-service (port 8001)
- FastAPI + httpx + per-file JSON storage (`reviews/<uuid>.json`)
- Calls `prompt-service` over HTTP to fetch and verify prompts
- Returns `404` if the prompt doesn't exist, `503` if prompt-service is
  unreachable
- Endpoints: `POST /reviews`, `GET /reviews`, `GET /reviews/{id}`,
  `GET /reviews/{prompt_id}/summary`

### frontend
- Vite + React, calls both services via relative paths (`/prompts`, `/reviews`)
- In dev, Vite's proxy forwards these to the two backend ports directly
- In production, nginx performs the same routing

## Setup

### 1. Postgres
Create the database (one-time):
```sql
CREATE DATABASE prompt_manager;
```

### 2. prompt-service
```
cd prompt-service
python -m venv venv
venv\Scripts\activate          (Windows)  /  source venv/bin/activate (Mac/Linux)
pip install -r requirements.txt
```
Edit `.env` and set your real Postgres password:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/prompt_manager
SERVICE_PORT=8000
```
Run:
```
uvicorn main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` to confirm all 6 endpoints via Swagger UI.

### 3. review-service
```
cd review-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```
`.env` (already correct by default, no edits needed):
```
PROMPT_SERVICE_URL=http://localhost:8000
SERVICE_PORT=8001
```
Visit `http://localhost:8001/docs` to confirm all 4 endpoints.

### 4. Frontend
```
cd frontend
npm install
npm run build
```
This produces `frontend/dist/`, which nginx will serve.

### 5. nginx
Edit `nginx.conf` at the repo root: replace the `root` path with the absolute
path to your `frontend/dist` folder (forward slashes, quoted if it contains
spaces). Copy it into your nginx installation's `conf/nginx.conf`, then:
```
nginx.exe -t          (test config)
nginx.exe              (start)
```
Visit `http://localhost`.

## Running everything together

All three must run simultaneously:
1. `uvicorn main:app --reload --port 8000` (prompt-service)
2. `uvicorn main:app --reload --port 8001` (review-service)
3. `nginx.exe` (frontend + routing)

## Example requests

Create a prompt:
```
curl -X POST http://localhost:8000/prompts \
  -H "Content-Type: application/json" \
  -d '{"name": "Cold Email Opener", "content": "Write a cold email opener.", "tags": "sales,outbound"}'
```

Submit a review (replace `<id>` with the prompt's returned UUID):
```
curl -X POST http://localhost:8001/reviews \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": "<id>", "reviewer_name": "Ahad", "score": 4, "feedback": "Good, a bit generic."}'
```

Get a prompt's review summary:
```
curl http://localhost:8001/reviews/<id>/summary
```

## Design notes

- **Why SQLAlchemy instead of raw SQL for prompt-service**: the original
  spec asked for raw `sqlite3`; a later live instruction specified Postgres
  instead, and SQLAlchemy is the standard ORM pairing for Postgres + FastAPI.
- **Why review-service still has no database**: this boundary is the core
  architectural lesson of the project and wasn't affected by the Postgres
  change — review-service only ever talks to prompt-service over HTTP.
- **Why JSON files for review-service, not Postgres too**: deliberate
  contrast in persistence patterns, as specified in the original brief.
- **404 vs 503**: a 404 means prompt-service responded and said "not found";
  a 503 means prompt-service itself could not be reached at all. These are
  distinguished using `httpx.RequestError` (network failure) vs checking
  `response.status_code` (an actual HTTP response).
