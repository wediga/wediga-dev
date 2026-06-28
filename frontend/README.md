# frontend

Next.js 16 (App Router) frontend for wediga.dev. It renders the public and
recruiter views and talks to the FastAPI backend only through its own BFF
route handlers under `app/api`. The browser never reaches the backend directly.

## Development

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
```

The build emits a standalone output (`output: "standalone"` in
`next.config.ts`) that the deploy image in `../deploy/Dockerfile.frontend`
runs with `node server.js`.
