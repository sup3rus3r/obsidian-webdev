# Fullstack Skill — Obsidian WebDev Agent

You are working on a **fullstack project** inside `/workspace`. This is a combined frontend + backend project in a single container. Follow these rules exactly.

---

## Environment

- Frontend: typically Next.js or React — check `package.json` at `/workspace` root or `/workspace/frontend/`
- Backend: typically FastAPI or Express — check for `pyproject.toml` (FastAPI) or `package.json` with express/hono (Node backend)
- Tailwind CSS v4 if frontend is present
- Package manager: **npm** for Node, **uv** for Python
- Dev server already running via tmux — **never restart manually**
- Ports: frontend on **3000**, backend on **8000** (or check `package.json` / `pyproject.toml`)

---

## Step 1 — Orient yourself before ANY work

Run these immediately when starting a task on an unfamiliar fullstack project:

```
list_files_brief("/workspace")
```

Then identify the structure. Common patterns:

### Pattern A — Monorepo (separate dirs)
```
/workspace
  frontend/      ← React or Next.js
  backend/       ← FastAPI or Node
  docker-compose.yml
```

### Pattern B — Next.js fullstack (API routes + frontend together)
```
/workspace
  app/           ← Next.js App Router (pages + API routes)
  lib/           ← shared logic
  prisma/ or db/ ← database
```

### Pattern C — Node fullstack
```
/workspace
  src/
    client/      ← React frontend
    server/      ← Express/Hono backend
```

Read `package.json` and (if present) `pyproject.toml` to confirm frameworks and versions before writing any code.

---

## Working in a monorepo

### Installing dependencies

```bash
# Frontend
cd frontend && npm install <pkg>

# Backend (Python)
cd backend && uv add <pkg>

# Backend (Node)
cd backend && npm install <pkg>
```

### Running checks

```bash
# Frontend build check
cd frontend && npm run build 2>&1 | tail -20

# Backend import check (Python)
cd backend && uv run python -c "from main import app; print('OK')"

# Backend start check (Node)
cd backend && node -e "require('./src/index')" 2>&1 | head -5
```

---

## API communication between frontend and backend

### Frontend → Backend calls

Always use environment variables for the API URL — never hardcode:

```tsx
// Next.js
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// React/Vite
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
```

### CORS (FastAPI backend)

If you add a new frontend origin, update CORS in the backend:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Skills to apply per layer

For the **frontend layer**, apply the matching skill:
- Next.js → see `nextjs.md` rules + Context7 calls
- React/Vite → see `react.md` rules + Context7 calls
- Tailwind → always apply `tailwind.md`

For the **backend layer**, apply the matching skill:
- FastAPI → see `fastapi.md` rules + Context7 calls
- Express/Hono → fetch docs via Context7 (see below)

---

## Context7 — fetch docs for both layers

### Next.js / React — same as their standalone skill files

Next.js:
```
web_fetch("https://context7.com/api/v1/nextjs/nextjs/docs?tokens=8000&topic=<TOPIC>")
```

React:
```
web_fetch("https://context7.com/api/v1/facebook/react/docs?tokens=8000&topic=<TOPIC>")
```

### FastAPI
```
web_fetch("https://context7.com/api/v1/tiangolo/fastapi/docs?tokens=8000&topic=<TOPIC>")
```

### Express.js
```
web_fetch("https://context7.com/api/v1/expressjs/express/docs?tokens=6000&topic=<TOPIC>")
```

Topics: `routing`, `middleware`, `error-handling`, `static-files`, `request-response`

### Hono
```
web_fetch("https://context7.com/api/v1/honojs/hono/docs?tokens=6000&topic=<TOPIC>")
```

Topics: `routing`, `middleware`, `validation`, `rpc`, `websocket`

### Tailwind CSS v4
```
web_fetch("https://context7.com/api/v1/tailwindlabs/tailwindcss/docs?tokens=6000&topic=<TOPIC>")
```

### Prisma (if present)
```
web_fetch("https://context7.com/api/v1/prisma/prisma/docs?tokens=7000&topic=<TOPIC>")
```

Topics: `schema`, `client-queries`, `migrations`, `relations`, `filtering-sorting`

---

## What NOT to do

- Never assume the structure — always `list_files_brief` first
- Never install packages at the wrong level (frontend pkg in backend dir)
- Never hardcode ports or API URLs
- Never restart the dev server — it's running in tmux
- Never mix Python and Node package managers (`uv` for Python, `npm` for Node)
- Never apply Next.js-specific patterns (App Router, RSC) to a React/Vite frontend

---

## Git integration

SSH key is pre-injected. Commit from `/workspace`:
```bash
git status
git add -A && git commit -m "feat: add user authentication"
git push origin main
```
