# wediga-dev

**Personal landing page with role-based access control.**

[Live](https://wediga.dev)

> A personal web presence that respects privacy by default. Role-based access control ensures that different audiences see exactly what's meant for them — and nothing more.

---

## Why This Exists

I wanted a personal site that isn't just a static page, but also doesn't dump everything into the public. Some things should be open to everyone, some only to people I invite, and my personal data shouldn't sit around for scrapers. The old version was a two-link page with its logins hardcoded in an `.env`, and every change meant editing files on the server, so I rebuilt it around a real datastore with an admin area to manage the content.

What came out is one site with three faces. The public landing stays minimal, a protected area opens only for invited visitors, and an admin area is where I run all of it.

## What It Does

The public landing is a single animated page with my skills and a legal imprint, and nothing beyond that. Invited visitors reach the rest through a personal, revocable link, which opens the full portfolio, my CV as a downloadable PDF with an inline preview, and my contact details. From the admin area I edit the content, upload the CV, hand out or revoke those links, and curate the mirrored GitHub repositories. Sessions are cookie-based with CSRF protection and rate limiting on the sensitive routes, and the content lives in a SQLite database so nothing personal ends up in the repo.

## Tech Stack

- **Next.js 16** (App Router) for the frontend, with a BFF layer so the browser never talks to the backend directly
- **FastAPI** on **Python 3.12** with **uv** for the backend
- **SQLite** for storage, signed session cookies for auth
- **Tailwind CSS** and a **Three.js** WebGL hero for the look
- **Docker** behind a **Caddy** reverse proxy, shipped via GitHub Actions

## Project Structure

```
wediga-dev/
  frontend/         # Next.js app (public, protected and admin views) + BFF route handlers
  backend/          # FastAPI app: auth, content, CV, recruiter links, GitHub sync, SQLite
  deploy/           # Dockerfiles, compose, Caddy snippet
  content.example/  # Sample content (in Git)
  content/          # Personal content (NOT in Git)
  data/             # SQLite database (NOT in Git)
  docs/             # Planning docs (NOT in Git)
```

## Run Locally

The backend and frontend run as two processes. Start the backend first:

```bash
cd backend
uv sync
cp ../.env.example ../.env   # then fill in the secrets
uv run python -m app.db.migrate
uv run uvicorn app.main:app --reload   # http://localhost:8000
```

Then the frontend, which reaches the backend over `BACKEND_URL` (default `http://localhost:8000`):

```bash
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

## Docker

```bash
cd deploy
docker compose up --build
```

The database and content are mounted as volumes, so they change without rebuilding the images.

## License

MIT
