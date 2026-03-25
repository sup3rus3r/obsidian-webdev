# React (Vite) Skill — Obsidian WebDev Agent

You are working on a **React + Vite project** inside `/workspace`. Follow these rules exactly.

---

## Environment

- React **18.x or 19.x** — check `package.json` to confirm version
- Vite **5.x** — bundler and dev server
- TypeScript **5.x** — strict mode, always typed
- Tailwind CSS **v4** — see tailwind.md for full rules
- Package manager: **npm** only
- Runtime: Node.js inside Docker container, port **5173**
- Dev server already running via tmux — **never run `npm run dev` again**

---

## File structure rules

```
/workspace
  src/
    main.tsx               ← entry point — do NOT modify unless adding providers
    App.tsx                ← root component and router setup
    pages/                 ← route-level components (one file per route)
    components/            ← reusable UI components
      ui/                  ← primitive UI only (Button, Input, Card, etc.)
    hooks/                 ← custom React hooks (useX naming)
    lib/                   ← utilities, API clients, helpers
    types/                 ← TypeScript interfaces and types
    assets/                ← images, fonts, static files
  public/                  ← served as-is (favicon, robots.txt)
  index.html               ← Vite entry HTML — do not rename
  vite.config.ts           ← Vite config
```

- Never create a `pages/` folder at the root level — source lives in `src/`
- Keep components focused — one responsibility per file
- Barrel exports (`index.ts`) are acceptable for `components/ui/`

---

## Routing

Use **React Router v6** (or v7 if present in package.json — check first).

```tsx
// src/App.tsx — v6 pattern
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { DashboardPage } from './pages/DashboardPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

Install if missing: `npm install react-router-dom`

---

## Data fetching patterns

For simple fetches, use `useEffect` + `useState`. For anything complex, use TanStack Query if already installed:

```tsx
// Simple fetch
'use client' — NOT needed in React/Vite (no RSC)
import { useState, useEffect } from 'react'

export function useItems() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/items')
      .then(r => r.json())
      .then(data => { setItems(data); setLoading(false) })
  }, [])

  return { items, loading }
}
```

Check `package.json` before choosing — use what's already installed.

---

## Component patterns

### Typed functional component
```tsx
// src/components/UserCard.tsx
interface UserCardProps {
  name: string
  email: string
  avatar?: string
}

export function UserCard({ name, email, avatar }: UserCardProps) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-lg border">
      {avatar && <img src={avatar} alt={name} className="w-10 h-10 rounded-full" />}
      <div>
        <p className="font-medium">{name}</p>
        <p className="text-sm text-gray-500">{email}</p>
      </div>
    </div>
  )
}
```

### Custom hook
```tsx
// src/hooks/useLocalStorage.ts
import { useState } from 'react'

export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key)
      return stored ? JSON.parse(stored) : initial
    } catch {
      return initial
    }
  })

  const set = (v: T) => {
    setValue(v)
    localStorage.setItem(key, JSON.stringify(v))
  }

  return [value, set] as const
}
```

---

## Environment variables

Vite env vars must be prefixed with `VITE_` to be accessible in the browser:
```tsx
const apiUrl = import.meta.env.VITE_API_URL
```

Define in `.env` or `.env.local` at project root.

---

## What NOT to do

- Never use `'use client'` or `'use server'` — those are Next.js only
- Never use `next/link`, `next/image`, `next/navigation` — wrong framework
- Never use `create-react-app` patterns (`react-scripts`) — this is Vite
- Never use `process.env.X` for browser variables — use `import.meta.env.VITE_X`
- Never run `npm run dev` — already running
- Never use class components — functional components only
- Never use `ReactDOM.render()` — use `createRoot()` (already in `main.tsx`)

---

## Building and verifying

```bash
npm run build          # TypeScript compile + Vite build
npm run lint           # ESLint check
```

Always run build after significant changes to catch TypeScript errors.

---

## Context7 — ALWAYS fetch docs before writing code

Use `web_fetch` to get current React and Vite documentation **before starting any significant feature**.

### React docs via Context7

```
GET https://context7.com/api/v1/facebook/react?tokens=8000&topic=<TOPIC>
```

| What you are building | Topic to use |
|---|---|
| Hooks (useState, useEffect, etc.) | `hooks-reference` |
| useReducer / complex state | `use-reducer` |
| Context API | `use-context-context-api` |
| Custom hooks | `reusing-logic-custom-hooks` |
| Refs and DOM access | `use-ref-manipulating-dom` |
| Concurrent features | `use-transition-use-deferred-value` |
| Forms and controlled inputs | `forms-controlled-uncontrolled` |
| Error boundaries | `error-boundaries` |
| Portals | `portals` |
| Performance / memo | `use-memo-use-callback-memo` |

**Call example:**
```
web_fetch("https://context7.com/api/v1/facebook/react?tokens=8000&topic=hooks-reference")
```

### React Router docs via Context7

```
GET https://context7.com/api/v1/remix-run/react-router?tokens=6000&topic=<TOPIC>
```

| What you are building | Topic |
|---|---|
| Basic routing setup | `getting-started-routing` |
| Nested routes | `nested-routes` |
| Route params | `url-params` |
| Navigation (useNavigate) | `use-navigate` |
| Loaders and actions | `loaders-actions` |
| Protected routes | `auth-protected-routes` |

### Vite docs via Context7

```
GET https://context7.com/api/v1/vitejs/vite?tokens=5000&topic=<TOPIC>
```

Topics: `env-variables`, `static-assets`, `build-options`, `plugins`, `proxy`

---

## Tailwind CSS v4

Fetch before using:
```
web_fetch("https://context7.com/api/v1/tailwindlabs/tailwindcss.com?tokens=5000&topic=<TOPIC>")
```

---

## Git integration

SSH key is pre-injected. Use git directly:
```bash
git status
git add -A && git commit -m "feat: add user card component"
git push origin main
```
