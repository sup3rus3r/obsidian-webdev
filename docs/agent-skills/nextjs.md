# Next.js Skill — Obsidian WebDev Agent

You are working on a **Next.js project** inside `/workspace`. Follow these rules exactly.

---

## Environment

- Next.js **16.x** (App Router — NOT Pages Router)
- React **19.x** — use new APIs: `use()`, `useActionState`, `useOptimistic` where appropriate
- TypeScript **5.x** — strict mode, always typed
- Tailwind CSS **v4** — see Tailwind skill section below
- Package manager: **npm** only (`npm install`, never `yarn` or `pnpm`)
- Runtime: Node.js inside Docker container, port **3000**
- Dev server already running via tmux — never run `npm run dev` again

---

## File structure rules

```
/workspace
  app/                     ← ALL routes go here (App Router)
    layout.tsx             ← root layout, do not delete
    page.tsx               ← root page
    [route]/
      page.tsx             ← route page (default export, async ok)
      layout.tsx           ← optional nested layout
      loading.tsx          ← optional Suspense boundary
      error.tsx            ← optional error boundary ('use client')
  components/              ← shared components
    ui/                    ← primitive UI only (Button, Input, etc.)
  lib/                     ← utilities, helpers, non-UI logic
  hooks/                   ← custom React hooks ('use client')
  types/                   ← TypeScript interfaces and types
  public/                  ← static assets
```

- Routes live in `app/` — never `pages/`
- Components that use hooks/events must have `'use client'` at the top
- Server Components are the default — keep them async where possible
- Never put business logic in `page.tsx` — extract to `lib/` or Server Actions

---

## Patterns to follow

### Server Components (default)
```tsx
// app/dashboard/page.tsx
export default async function DashboardPage() {
  const data = await fetchData()  // direct async/await, no useEffect
  return <div>{data.title}</div>
}
```

### Client Components
```tsx
'use client'
import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

### Server Actions
```tsx
// lib/actions.ts
'use server'
export async function createItem(formData: FormData) {
  const name = formData.get('name') as string
  // ... db logic
  revalidatePath('/items')
}
```

### API Routes (Route Handlers)
```tsx
// app/api/items/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  return NextResponse.json({ items: [] })
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  return NextResponse.json({ created: body }, { status: 201 })
}
```

---

## What NOT to do

- Never use `getServerSideProps`, `getStaticProps`, `getInitialProps` — these are Pages Router only
- Never use `useRouter` from `next/router` — use `next/navigation`
- Never use `<Link>` from anywhere except `next/link`
- Never use `next/head` — use `export const metadata` in layouts/pages instead
- Never create `pages/` directory
- Never run `npm run dev` — dev server is already running
- Never use `require()` — use ES module imports only
- Never hardcode ports — use environment variables

---

## Metadata pattern
```tsx
// app/dashboard/page.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Dashboard',
  description: 'Project dashboard',
}
```

---

## Context7 — ALWAYS fetch docs before writing code

The Context7 API gives you current, version-accurate Next.js documentation. Use `web_fetch` to retrieve it **before starting any significant feature**.

### How to use Context7

```
GET https://context7.com/api/v1/nextjs/nextjs/docs?tokens=8000&topic=<TOPIC>
```

Replace `<TOPIC>` with the specific thing you are about to implement. Examples:

| What you are building | Topic to use |
|---|---|
| Any new route or page | `app-router-routing-pages` |
| Data fetching | `data-fetching-server-components` |
| Server Actions / forms | `server-actions-forms` |
| Route Handlers (API) | `route-handlers` |
| Layouts, templates | `layouts-templates` |
| Metadata / SEO | `metadata-api` |
| Image optimization | `next-image` |
| Authentication patterns | `authentication` |
| Middleware | `middleware` |
| Dynamic routes | `dynamic-routes-catch-all` |
| Suspense / loading | `loading-ui-streaming` |
| Error handling | `error-handling` |

**Call example:**
```
web_fetch("https://context7.com/api/v1/nextjs/nextjs/docs?tokens=8000&topic=server-actions-forms")
```

Always fetch before writing — never rely on training knowledge for Next.js APIs. The framework changes rapidly.

---

## Tailwind CSS v4 — see tailwind.md for full rules

Key v4 differences active in this project:
- Config is in `app/globals.css` via `@theme` — NOT `tailwind.config.js`
- Use `@import "tailwindcss"` not `@tailwind base/components/utilities`
- Fetch Tailwind docs via Context7 before using any utility you are unsure about:
  ```
  web_fetch("https://context7.com/api/v1/tailwindlabs/tailwindcss/docs?tokens=5000&topic=<TOPIC>")
  ```

---

## Git integration

This project may have git configured. Use `bash` to run git commands inside the container:
```bash
git status
git add -A && git commit -m "feat: add dashboard page"
git push origin main
```
SSH key is pre-injected into `~/.ssh/` — push/pull works without credentials.
