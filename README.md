# wediga-dev

**Personal landing page with role-based access control.**

[Live](https://wediga.dev)

> A personal web presence that respects privacy by default. Role-based access control ensures that different audiences see exactly what's meant for them — and nothing more.

---

## Why This Exists

I wanted a personal site that isn't just a static page, but also doesn't dump everything into the public. Some things should be open to everyone, some only to people I invite, and my personal data shouldn't sit around for scrapers. The old version was a two-link page with its logins hardcoded in an `.env`, and every change meant editing files on the server, so I rebuilt it around a real datastore with an admin area to manage the content.

What came out is one site with three faces. The public landing stays minimal, a protected area opens only for invited visitors, and an admin area is where I run all of it.

## What It Does

The public landing is a single animated page with my skills and a legal imprint, and nothing beyond that. If a browser can't run the WebGL animation, the page switches to its quiet layout on its own and tells the visitor why, so nobody lands on an empty screen. Invited visitors reach the rest through a personal, revocable link, which opens the full portfolio, my CV as a downloadable PDF with an inline preview, and my contact details. From the admin area I edit the content, upload the CV, hand out or revoke those links, and curate the mirrored GitHub repositories. Sessions are cookie-based with CSRF protection and rate limiting on the sensitive routes, and the content, the CV included, lives in a PostgreSQL database so nothing personal ends up in the repo.

## Tech Stack

- **Next.js 16** (App Router) for the frontend, with a BFF layer so the browser never talks to the backend directly
- **FastAPI** on **Python 3.12** with **uv** for the backend
- **PostgreSQL** with **SQLAlchemy** and **Alembic** migrations for storage, signed session cookies for auth
- **Tailwind CSS** and a **Three.js** WebGL hero for the look
- Container images built and scanned in GitHub Actions, running under rootless **Podman** behind a **Caddy** reverse proxy
- **authentik** as a self-hosted identity provider on its own subdomain, with its setup kept in a blueprint file. The site does not sign anyone in through it yet

## Project Structure

```
wediga-dev/
  frontend/         # Next.js app (public, protected and admin views) + BFF route handlers
  backend/          # FastAPI app: auth, content, CV, recruiter links, GitHub sync, migrations
  deploy/           # Dockerfiles, Quadlet units, backup timers, authentik blueprint
  content.example/  # Sample content (in Git)
  content/          # Personal content (NOT in Git)
  docs/             # Planning docs (NOT in Git)
```

## Run Locally

The backend needs a PostgreSQL. Locally I run the same image as production in Podman, trusting every connection on `127.0.0.1`, so no password is checked. The tests run against the same container:

```bash
podman run -d --name wediga-db-test -p 127.0.0.1:5432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust docker.io/library/postgres:18.6-alpine
```

The backend and frontend run as two processes. Start the backend first, with the connection in the environment:

```bash
cd backend
uv sync
cp ../.env.example ../.env   # then fill in the secrets
export POSTGRES_USER=postgres POSTGRES_DB=postgres POSTGRES_PASSWORD=unused POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432
uv run alembic upgrade head
uv run uvicorn app.main:app --reload   # http://localhost:8000
uv run pytest                          # tests, against the container above
uv run ruff format .                   # format the code
uv run ruff check .                    # lint
```

Then the frontend, which reaches the backend over `BACKEND_URL` (default `http://localhost:8000`):

```bash
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

Production runs both as container images from the Quadlet units in `deploy/quadlet/`, and `deploy/README.md` describes how the server is laid out and what a deploy does.

## License

MIT
