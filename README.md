# wediga-dev

**Personal landing page with role-based access control.**

[Live](https://wediga.dev)

> A personal web presence that respects privacy by default. Role-based access control ensures that different audiences see exactly what's meant for them — and nothing more.

---

## Why This Exists

I wanted a personal site that isn't just a static page, but also doesn't dump everything into the public. Some information should be accessible to everyone, some only to specific people, and personal data shouldn't be sitting out in the open for scrapers.

So I built a simple auth system with different roles. Each role gets its own view. The public side stays minimal, the protected side shows what it needs to, and the content lives outside the codebase so the repo can stay public.

---

## What It Does

Three-tier access model with session-based authentication:

```
wediga.dev (PUBLIC)
├─ Minimal landing page
├─ Project links
└─ Login

wediga.dev/... (PROTECTED - Role A)
├─ Detailed content
└─ Full profile

wediga.dev/... (PROTECTED - Role B)
├─ Private links
└─ Tools
```

- Multiple user roles with separate views
- Session-based auth via middleware
- Content loaded from external files (not in Git)
- Public repo, private data

---

## Tech Stack

- **Python 3.12** with **uv** for dependency management
- **FastAPI** for the backend and routing
- **Jinja2** for server-side template rendering
- **Starlette Sessions** for authentication
- **Tailwind CSS** (via CDN) for styling
- **Docker** for containerization and deployment

---

## Project Structure

```
wediga-dev/
├── main.py              # FastAPI app with auth logic
├── content_loader.py    # Loads content from Markdown/JSON
├── templates/           # Jinja2 HTML templates
├── content/             # Personal content (NOT in Git)
├── content.example/     # Content templates (in Git)
├── .env                 # Secrets (NOT in Git)
├── Dockerfile
├── compose.yaml
└── pyproject.toml
```

---

## Setup

### Local Development

```bash
git clone https://github.com/wediga/wediga-dev.git
cd wediga-dev
uv sync
cp -r content.example content
cp .env.example .env
# Edit .env and content/ with your data
uv run uvicorn main:app --reload
```

### Docker

```bash
docker compose up --build
```

---

## License

MIT
