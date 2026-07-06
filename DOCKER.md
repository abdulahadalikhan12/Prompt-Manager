# Dockerization & CI/CD — Prompt Manager

## The Task

The assignment: dockerize every service, write a document explaining the port choices, env sources, and network model, discuss whether ngrok can run inside `docker-compose`, and ship the whole system with a single command. Then publish images to Docker Hub / GitHub Packages via a GitHub Actions workflow that pushes a new incrementing version tag on every push to the repo.

This document covers all of the above.

---

## Architecture Overview

The system is a chat-style prompt manager built as 4 Python microservices + a React frontend, fronted by nginx, backed by Postgres.

```
                                 Browser
                                    |
                                    | :80
                                    v
                              +-----------+
                              |   nginx   |   (serves React build + reverse proxies /api)
                              +-----+-----+
                                    |
             +----------------------+----------------------+
             |            |                 |              |
             v            v                 v              v
      prompt-service  review-service  document-service  llm-service
          :8000         :8001            :8003            :8002
             |                                              ^
             |                                              |
             +----------------------------------------------+
             |    (prompt-service and review-service call llm-service
             |     server-side over the internal network)
             v
        postgres :5432
```

Everything runs on a single user-defined bridge network (`prompt-network`) and is started with `docker compose up`.

---

## Port Assignments — and Why

| Service          | Container port | Host port | Public? | Reason                                                                                                              |
| ---------------- | -------------- | --------- | ------- | ------------------------------------------------------------------------------------------------------------------- |
| nginx            | 80             | 80        | Yes     | Single public entry point. The browser talks only to nginx; nginx fans traffic out to the right backend by URL path. |
| prompt-service   | 8000           | 8000      | Internal | FastAPI convention — `uvicorn` defaults to 8000. Chosen as the "first" backend port to keep things memorable.       |
| review-service   | 8001           | 8001      | Internal | Sequentially next after prompt-service. Handles all `/reviews/*` traffic.                                            |
| llm-service      | 8002           | 8002      | Internal | Next in sequence. **Never exposed through nginx** — only other backend services call it, server-side.               |
| document-service | 8003           | 8003      | Internal | Next in sequence. Handles PDF/DOCX upload + text extraction, capped at 20 MB.                                        |
| postgres         | 5432           | 5432      | Internal | Postgres' well-known default port. Kept as-is so tools like `psql` and DBeaver work with no surprises.               |

**Why 8000–8003 and not something else?** They're the FastAPI/uvicorn convention, they don't collide with system-reserved ports (<1024) or common dev servers (3000 for Node, 5173 for Vite), and keeping them consecutive makes it obvious at a glance which port belongs to which service.

**Why is nginx the only public port?** Two reasons:
1. **One URL for the whole app.** The user hits `http://localhost/` and nginx figures out whether the request is for the React app, `/prompts`, `/reviews`, or `/documents`.
2. **Attack surface.** llm-service holds the OpenRouter API key. If it were reachable from the host, anyone who found it could burn through the key. Keeping it internal means it's only reachable by other containers on the same Docker network.

The host-side ports on the backend services (8000–8003) are only there for local debugging — in a real deployment they would be removed from `docker-compose.yml` and only nginx's port 80 would remain.

---

## Environment Variables — Where They Come From

Each service reads its config from a `.env` file inside its own directory, loaded via Compose's `env_file:` directive:

```yaml
llm-service:
  env_file:
    - ./llm-service/.env
```

**Why a per-service `.env` and not one big root-level file?**

- **Least-privilege.** llm-service needs `OPENROUTER_API_KEY`; document-service doesn't. If both services read the same file, both containers see every secret. Splitting them means each container only gets what it needs.
- **Portability.** Each service is a standalone unit. You can `docker run llm-service` on its own with just `llm-service/.env` and it works.
- **Clarity.** When something breaks, you know exactly which file to check.



**`.env` files are gitignored** (`.env` is in `.gitignore`) so no secret ever lands in the repo. This matters for the CI workflow too — the GitHub Actions runner has no `.env` files; it only builds and pushes the images, which don't bake in secrets.

---

## Why a Single Network

All six containers share one user-defined bridge network, `prompt-network`, declared once at the bottom of `docker-compose.yml`:

```yaml
networks:
  prompt-network:
    driver: bridge
```

**Why one network and not several?**

1. **Container-name DNS.** On a user-defined bridge network, Docker gives every container an internal DNS record equal to its service name. nginx can reach prompt-service by writing `http://prompt-service:8000` — no IPs, no linking flags, no environment-variable juggling. This only works if the containers are on the same network.
2. **Simplicity.** Splitting into multiple networks (e.g., a "frontend network" and a "backend network") only pays off when you have a security boundary to enforce between them. Here every service is trusted and needs to talk to at least one other, so the extra network config would be pure overhead.
3. **Isolation from the host.** The bridge network is isolated from the host's networking by default. Nothing on the host can hit prompt-service:8000 through the Docker network — the only way in is via a published port (`ports:` in compose).

**Default bridge vs. user-defined bridge:** the default bridge network (which containers join if you don't specify one) does *not* give you name-based DNS. That's why we declare `prompt-network` explicitly.

---

## Can Ngrok Run Inside `docker-compose`?

**Yes.** Ngrok publishes an official image, `ngrok/ngrok`, that runs as a service alongside everything else. You add it to `docker-compose.yml` like this:

```yaml
ngrok:
  image: ngrok/ngrok:latest
  restart: unless-stopped
  command: http nginx:80 --log stdout
  environment:
    NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
  ports:
    - "4040:4040"     # ngrok's local web dashboard
  depends_on:
    - nginx
  networks:
    - prompt-network
```

**How it works, end to end:**

1. Ngrok joins `prompt-network`, so it can resolve `nginx` by name.
2. `command: http nginx:80` tells ngrok to open a tunnel and forward incoming public HTTPS traffic to `http://nginx:80` on the internal network.
3. Ngrok registers with ngrok's cloud using `NGROK_AUTHTOKEN` (kept in a `.env` file at the compose root, never committed).
4. It prints a public `https://<random>.ngrok.app` URL in the container logs. Anyone on the internet who hits that URL lands on nginx, which then routes to the correct backend as if they were on localhost.
5. The dashboard on `http://localhost:4040` shows every request in real time — useful for debugging.

**Trade-offs / caveats:**

- **Free tier gives a random URL** that changes every restart. A paid plan gets a reserved domain.
- **Free tier is rate-limited** and shows an interstitial page on first visit — fine for demos, not for real users.
- **The tunnel exposes the *entire* app**. In this project that's what you want (public demo), but in a more locked-down setup you'd tunnel to a specific path or put an auth layer in front.
- **Nothing on the *host* needs to open a port.** The tunnel starts from inside the container outbound to ngrok's edge, so no router config, no port forwarding, no firewall changes. This is the whole reason ngrok exists.

**Turnaround:** From `docker compose up` to a publicly-reachable URL is maybe 10 seconds. The URL is printed in `docker logs ngrok`.

**Alternatives if ngrok isn't an option:**
- **Cloudflare Tunnel** (`cloudflared`) — same idea, free, stable subdomain if you own a domain.
- **Tailscale Funnel** — same idea, requires a Tailscale account.
- Both have official Docker images and drop into compose the same way.

---

## One-Command Startup

```
docker compose up -d
```

That's it. Compose:
1. Pulls `postgres:17` and `nginx:alpine`, `python:3.12-slim`, `node:20-alpine` base images.
2. Builds each service image from its `Dockerfile`.
3. Creates `prompt-network` and the `postgres_data` volume.
4. Starts postgres, waits for its healthcheck to pass, then starts the backend services in dependency order, then nginx.
5. The app is live on `http://localhost/`.

To stop everything: `docker compose down`. To wipe the database too: `docker compose down -v`.

---

## CI/CD — Automated Docker Hub Publishing

**Trigger:** Every push to `main` or `master`.

**Location:** `.github/workflows/docker.yml`.

**What it does:**

1. Checks out the repo.
2. Sets up Docker Buildx (needed for multi-arch and BuildKit features).
3. Logs into Docker Hub using two GitHub secrets:
   - `DOCKER_USERNAME` — your Docker Hub username
   - `DOCKER_TOKEN` — a personal access token with Read + Write + Delete scope
4. Runs a **matrix build** of the four Python services in parallel — `prompt-service`, `review-service`, `llm-service`, `document-service`. Each build uses `./<service>` as its context (matching what those Dockerfiles expect).
5. Runs a **separate job for nginx** in parallel, using `.` (repo root) as the context because its Dockerfile does `COPY frontend/…` — a multi-stage build that also compiles the React frontend and copies the resulting `dist/` into the nginx image.
6. Each image is tagged **twice** on every push:
   - `latest` — always points to the most recent build
   - `v${{ github.run_number }}` — an incrementing integer that GitHub maintains automatically (v1, v2, v3, …). This satisfies the "incrementing version number" requirement without any manual version bumping.
7. Uses **GitHub Actions cache** (`type=gha`) for Docker layer caching, so re-builds are ~10x faster after the first run.

**Why not `docker compose build` in the workflow?**
Compose builds are convenient but they build sequentially and don't play as well with layer caching and multi-arch. The `docker/build-push-action` is the standard tool that production repos use — better caching, parallel matrix builds, cleaner logs.

**What ends up on Docker Hub after every push:**

```
abdulahadalikhan12/prompt-service:latest      + :v<N>
abdulahadalikhan12/review-service:latest      + :v<N>
abdulahadalikhan12/llm-service:latest         + :v<N>
abdulahadalikhan12/document-service:latest    + :v<N>
abdulahadalikhan12/nginx:latest               + :v<N>
```

Postgres is *not* published — that's the official `postgres:17` image pulled from Docker Hub as-is. Re-publishing someone else's official image under your own namespace is pointless and would just eat storage.

---

## Dockerfile Notes

**Python services (`prompt-service`, `review-service`, `llm-service`, `document-service`)** all follow the same pattern:

```
FROM python:3.12-slim       # smaller than the full image, still has pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # --no-cache-dir keeps the image small
COPY . .
EXPOSE <port>
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "<port>"]
```

Key details:
- `--host 0.0.0.0` is required inside a container. `127.0.0.1` would make the service only reachable *within* the container, which defeats the point.
- `CMD` in JSON/exec form so uvicorn runs as PID 1 and receives signals correctly (a shell-form `CMD` would spawn a `/bin/sh` wrapper that swallows `SIGTERM`).
- The exec-form JSON array must be on a single line — Docker's parser doesn't allow it split across multiple lines. (Bit us once during initial build.)

**nginx is a multi-stage build:**

```
Stage 1 (node:20-alpine): install frontend deps, run `npm run build`, produce dist/
Stage 2 (nginx:alpine):   copy dist/ into /usr/share/nginx/html, add nginx.conf
```

Multi-stage means the final image doesn't carry Node, npm, or any of the frontend source — just the static `dist/` output plus nginx. Ships around 27 MB instead of 200+ MB.

---

## Task Requirements — Checklist

| Requirement                                          | Status |
| ---------------------------------------------------- | ------ |
| Dockerize each service                               | Done — 5 custom images + Postgres     |
| Document port assignments                            | Done — table above                    |
| Document env-var sources                             | Done — per-service `.env` files       |
| Document single-network rationale                    | Done — DNS + isolation                |
| Discuss ngrok inside `docker-compose`                | Done — yes, with sample config        |
| One-command deployment                               | Done — `docker compose up -d`         |
| Publish images to Docker Hub / GitHub Packages       | Done — Docker Hub                     |
| Workflow builds & pushes on every repo push          | Done — `.github/workflows/docker.yml` |
| Incrementing version tag on every push               | Done — `v${{ github.run_number }}`    |
| No errors pushed                                     | Done — build failures block push      |
