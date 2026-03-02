# Obsidian WebDev — Frontend Design System
> Research-backed guide for building an investor-grade, polished UI.
> Stack: Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui, AI SDK.

---

## Design Philosophy

Inspired by the best developer tools — Linear, Vercel, Cursor, v0.dev:
- **Dark-first**: default dark theme; light mode as secondary
- **Information density**: compact, purposeful UI with clear hierarchy
- **Fluid motion**: subtle, physics-based transitions — nothing flashy
- **Monochrome with accent**: near-black backgrounds, zinc/slate greys, single electric accent (violet or indigo)

---

## Color System

### Base Palette (OKLCH, dark-first)

```css
/* globals.css — dark mode as :root default */
:root {
  --background:    oklch(0.10 0.00 0);      /* near-black  */
  --foreground:    oklch(0.97 0.00 0);      /* near-white  */
  --card:          oklch(0.13 0.00 0);
  --card-foreground: oklch(0.97 0.00 0);
  --popover:       oklch(0.13 0.00 0);
  --muted:         oklch(0.17 0.00 0);
  --muted-foreground: oklch(0.55 0.00 0);
  --border:        oklch(0.22 0.00 0);
  --input:         oklch(0.18 0.00 0);
  --ring:          oklch(0.70 0.16 280);    /* violet accent ring */

  /* Primary accent — electric violet */
  --primary:       oklch(0.68 0.20 280);
  --primary-foreground: oklch(0.99 0.00 0);

  /* Secondary — subtle zinc */
  --secondary:     oklch(0.18 0.00 0);
  --secondary-foreground: oklch(0.97 0.00 0);

  /* Destructive */
  --destructive:   oklch(0.60 0.22 25);

  /* Chart colors */
  --chart-1: oklch(0.68 0.20 280);   /* violet  */
  --chart-2: oklch(0.75 0.15 200);   /* cyan    */
  --chart-3: oklch(0.78 0.16 145);   /* emerald */
  --chart-4: oklch(0.82 0.14 90);    /* amber   */
  --chart-5: oklch(0.65 0.22 25);    /* rose    */

  /* Sidebar */
  --sidebar:          oklch(0.12 0.00 0);
  --sidebar-border:   oklch(0.20 0.00 0);
  --sidebar-accent:   oklch(0.16 0.00 0);
  --sidebar-primary:  oklch(0.68 0.20 280);
}

.light {
  --background:    oklch(0.99 0.00 0);
  --foreground:    oklch(0.10 0.00 0);
  /* ... light overrides */
}
```

Use **tweakcn** (`https://tweakcn.com`) to fine-tune and generate the full palette interactively.

---

## shadcn/ui — Component Inventory

Install the CLI and add components as needed:

```bash
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add <component>
```

### Core Layout Components

| Component | Usage in Obsidian WebDev | Install |
|---|---|---|
| `Sidebar` | Main app navigation (collapsible icon mode) | `shadcn add sidebar` |
| `ResizablePanelGroup` | Workspace split panes | `shadcn add resizable` |
| `Sheet` | Slide-out drawers (mobile nav, quick settings) | `shadcn add sheet` |
| `Dialog` | Modals (create project, confirm delete) | `shadcn add dialog` |
| `Tabs` | Workspace panel switching (Editor / Preview / Terminal) | `shadcn add tabs` |
| `ScrollArea` | File tree, chat history, log output | `shadcn add scroll-area` |

### Data & Feedback

| Component | Usage | Install |
|---|---|---|
| `Table` + `DataTable` | Project list with sorting/filtering | `shadcn add table` |
| `Badge` | Build status (passed/failed/running) | `shadcn add badge` |
| `Progress` | Build progress bar | `shadcn add progress` |
| `Skeleton` | Loading states everywhere | `shadcn add skeleton` |
| `Sonner` (toast) | Build complete, error, export ready notifications | `shadcn add sonner` |
| `Alert` | Inline error messages | `shadcn add alert` |
| `Tooltip` | Icon button labels throughout workspace | `shadcn add tooltip` |

### Forms & Input

| Component | Usage | Install |
|---|---|---|
| `Command` | Global command palette (⌘K) | `shadcn add command` |
| `Select` | Framework picker, model picker | `shadcn add select` |
| `Input` | Chat input, project name, search | `shadcn add input` |
| `Textarea` | Multi-line prompts | `shadcn add textarea` |
| `Switch` | Settings toggles | `shadcn add switch` |
| `Separator` | Section dividers | `shadcn add separator` |

### Navigation

| Component | Usage | Install |
|---|---|---|
| `Breadcrumb` | Workspace file path | `shadcn add breadcrumb` |
| `DropdownMenu` | User menu, file context menu | `shadcn add dropdown-menu` |
| `ContextMenu` | File tree right-click | `shadcn add context-menu` |
| `Collapsible` | File tree expand/collapse | `shadcn add collapsible` |

### Charts (Recharts-based)
```bash
pnpm dlx shadcn@latest add chart
```
Use **Area Chart** for build timeline, **Bar Chart** for file counts per agent.

---

## Blocks (Pre-built Layouts)

These shadcn blocks serve as starting points — copy and adapt:

| Block | Use for |
|---|---|
| **Dashboard + Sidebar** | Main app shell with collapsible sidebar |
| **Sidebar with submenu** | Nested project/file navigation |
| **Auth — Login + image** | Landing/login page (split: form left, hero right) |
| **Data table** | Project list page |

Access at: `https://ui.shadcn.com/blocks`

---

## Third-Party Libraries

### AI SDK (Vercel)
```bash
pnpm add ai @ai-sdk/react
```
**NOT used for agent calls** (we have a custom WebSocket streaming setup), but `useChat`
is useful for any prompt-assistance features or inline AI suggestions in the editor.

Key hooks:
- `useChat` — streaming chat with auto-state management
- `useCompletion` — single-shot text completions
- `useObject` — stream structured JSON objects

### Animation — Motion
```bash
pnpm add motion
```
(Formerly Framer Motion, now `motion` package)

Patterns for Obsidian WebDev:
```tsx
// Streaming token fade-in
<motion.span
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.1 }}
>
  {token}
</motion.span>

// Panel slide-in
<motion.div
  initial={{ x: -20, opacity: 0 }}
  animate={{ x: 0, opacity: 1 }}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
/>

// Build status pulse
<motion.div
  animate={{ scale: [1, 1.05, 1] }}
  transition={{ repeat: Infinity, duration: 1.5 }}
/>
```

### Syntax Highlighting — Shiki
```bash
pnpm add shiki
```

Use React Server Components pattern for static code blocks:
```tsx
// components/CodeBlock.tsx (server component)
import { codeToHtml } from "shiki"

export async function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const html = await codeToHtml(code, {
    lang,
    theme: "github-dark-default",  // or "vesper" for warmer dark
  })
  return <div dangerouslySetInnerHTML={{ __html: html }} />
}
```

For chat streaming tokens (client), use `"github-dark-default"` or `"tokyo-night"` theme.

### Monaco Editor
```bash
pnpm add @monaco-editor/react
```

Setup:
```tsx
import Editor from "@monaco-editor/react"

<Editor
  height="100%"
  defaultLanguage="typescript"
  theme="vs-dark"               // or custom theme matching app palette
  options={{
    fontSize: 13,
    fontFamily: "JetBrains Mono, Fira Code, monospace",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    padding: { top: 16 },
    renderLineHighlight: "gutter",
  }}
/>
```

Custom dark theme matching app palette:
```tsx
monaco.editor.defineTheme("webdev-dark", {
  base: "vs-dark",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#0f0f0f",
    "editor.lineHighlightBackground": "#1a1a1a",
  },
})
```

### Terminal — xterm.js
```bash
pnpm add @xterm/xterm @xterm/addon-fit @xterm/addon-attach @xterm/addon-web-links
```

Key setup (client component):
```tsx
"use client"
import { useEffect, useRef } from "react"
import { Terminal } from "@xterm/xterm"
import { FitAddon } from "@xterm/addon-fit"
import { AttachAddon } from "@xterm/addon-attach"

export function TerminalPanel({ projectId }: { projectId: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const terminal = new Terminal({
      theme: { background: "#0f0f0f", foreground: "#e5e5e5" },
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 13,
      cursorBlink: true,
    })
    const fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    terminal.open(containerRef.current!)
    fitAddon.fit()

    const ws = new WebSocket(`/ws/terminal/${projectId}?token=...`)
    terminal.loadAddon(new AttachAddon(ws))

    const observer = new ResizeObserver(() => fitAddon.fit())
    observer.observe(containerRef.current!)
    return () => { terminal.dispose(); ws.close(); observer.disconnect() }
  }, [projectId])

  return <div ref={containerRef} className="h-full w-full" />
}
```

### Dark Mode — next-themes
```bash
pnpm add next-themes
```

```tsx
// app/layout.tsx
import { ThemeProvider } from "@/components/theme-provider"

<html lang="en" suppressHydrationWarning>
  <body>
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  </body>
</html>
```

### Icons — lucide-react
Already installed with shadcn. Key icons for Obsidian WebDev:
- `Sparkles`, `Bot`, `Cpu` — AI/agent indicators
- `FolderTree`, `File`, `FileCode2` — file tree
- `Terminal`, `Play`, `Square`, `RefreshCw` — build controls
- `ChevronRight`, `ChevronDown` — tree expand
- `Layers`, `Package`, `Globe` — framework icons
- `CheckCircle2`, `XCircle`, `AlertCircle`, `Loader2` — status indicators

---

## Screen-by-Screen Design Guide

### 1. Auth / Landing Page

**Layout:** Split screen — left: branding/hero, right: form
**Components:** `Card`, `Input`, `Button`, `Separator`
**Key design choices:**
- Dark background with subtle radial gradient from accent color at top
- Large bold headline: `text-4xl font-bold tracking-tight`
- Animated gradient text for product name (`bg-gradient-to-r from-violet-400 to-cyan-400`)
- Social proof: small badges showing "Built with Claude / GPT-4"

```
┌─────────────────────────────────────────────────┐
│                                                   │
│   ◈ Obsidian WebDev                                     │
│                                                   │
│   Build full-stack apps with AI.                  │
│   Describe your idea. Ship in minutes.            │
│                                                   │
│   [Agent-powered] [React + FastAPI] [Docker]      │
│                    │
├─────────────────────────────────────────────────┤
│  Sign in                        │
│  ┌────────────────────────────┐  │
│  │ Email                       │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ Password                    │  │
│  └────────────────────────────┘  │
│  [ Sign in ]                    │
└─────────────────────────────────────────────────┘
```

### 2. Project Dashboard

**Layout:** Sidebar + main content area
**Components:** `Sidebar` (collapsible), `DataTable`, `Badge`, `Button`, `DropdownMenu`
**Key design:**
- Projects as cards with framework badge + last build status + time ago
- "New Project" prominent CTA — gradient button
- Empty state: illustrated prompt with call-to-action

```
┌────────────────────────────────────────────────────────────┐
│  ◈  Obsidian WebDev     [Projects]  [Settings]       [User ▾]   │
├──────┬─────────────────────────────────────────────────────┤
│  Nav │  Projects                         [+ New Project]   │
│      │                                                      │
│  ⊞   │  ┌──────────────┐  ┌──────────────┐               │
│  Proj│  │ my-saas-app  │  │ todo-list    │               │
│      │  │ React        │  │ FastAPI      │               │
│  ⚙   │  │ ● Passed     │  │ ✗ Failed     │               │
│  Sett│  │ 2 hours ago  │  │ 1 day ago    │               │
│      │  └──────────────┘  └──────────────┘               │
└──────┴─────────────────────────────────────────────────────┘
```

### 3. Agent Workspace (Core Screen)

**Layout:** Resizable 4-panel workspace
**Components:** `ResizablePanelGroup`, `Tabs`, Monaco, xterm, Sidebar
**Key design:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ◈  my-saas-app  [Run ▶]  [Stop ■]  [Export]      ● Building  │
├───────────┬──────────────────────────────┬──────────────────────┤
│ File Tree │  Editor (Monaco)             │  Chat / Agent Log   │
│           │                              │                      │
│ ▼ src/    │  // App.tsx                  │  ┌─────────────────┐ │
│   App.tsx │  import { ... }              │  │ 🤖 Orchestrator │ │
│   main.tsx│                              │  │ Planning build...│ │
│ ▼ backend │  export default function App │  └─────────────────┘ │
│   main.py │    return <div>...</div>     │  ┌─────────────────┐ │
│           │  }                           │  │ ⚡ Frontend      │ │
│           │                              │  │ Writing App.tsx │ │
│           │                              │  └─────────────────┘ │
├───────────┴──────────────────────────────┤  ┌─────────────────┐ │
│  Terminal / Preview [Terminal] [Preview] │  │ You             │ │
│  $ npm run dev                           │  │ [____________]  │ │
│  Ready on http://localhost:3000          │  │ [    Send    ]  │ │
└──────────────────────────────────────────┴──────────────────────┘
```

### 4. Build Progress Panel

**Layout:** Slide-up sheet or right-side panel
**Components:** `Sheet`, `Progress`, `Badge`, `ScrollArea`, `Separator`
**Key design:**
- Stepper: Orchestrator → Frontend → Backend → DevOps → QA → Validator
- Each step: icon + name + status badge + elapsed time
- Live log tail below the stepper in monospace font
- Animated spinner on active step; checkmark on complete; X on error

---

## Typography

```css
/* Font stack */
font-family: "Geist", "Inter", system-ui, sans-serif;       /* UI */
font-family: "Geist Mono", "JetBrains Mono", monospace;     /* Code */
```

Install Geist (Vercel's font, perfect for developer tools):
```bash
pnpm add geist
```

```tsx
// app/layout.tsx
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"

<html className={`${GeistSans.variable} ${GeistMono.variable}`}>
```

---

## Animation Patterns

### Streaming text (agent tokens)
```tsx
// Each token fades in as it streams
{tokens.map((token, i) => (
  <motion.span
    key={i}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.08 }}
  >
    {token}
  </motion.span>
))}
```

### Status badge pulse (active build)
```tsx
// Pulsing dot for "building" state
<span className="relative flex h-2 w-2">
  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
  <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500" />
</span>
```

### Page transitions (Next.js App Router)
```tsx
// Use motion.div wrapping page content
<motion.main
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2, ease: "easeOut" }}
>
  {children}
</motion.main>
```

---

## npm Packages Summary

```bash
# shadcn/ui (install components individually)
pnpm dlx shadcn@latest init

# Core UI
pnpm add geist next-themes

# Animation
pnpm add motion

# AI streaming UI
pnpm add ai @ai-sdk/react

# Code editor
pnpm add @monaco-editor/react

# Terminal
pnpm add @xterm/xterm @xterm/addon-fit @xterm/addon-attach @xterm/addon-web-links

# Syntax highlighting
pnpm add shiki

# File tree (optional, or build custom with shadcn Collapsible)
pnpm add react-arborist

# Date formatting (for "2 hours ago" etc.)
pnpm add date-fns

# Class helpers (already with shadcn)
# clsx, tailwind-merge, class-variance-authority
```

---

## Key Design Rules (for AI agents building this)

1. **Dark-first** — use `dark:` variants sparingly; dark IS the default theme
2. **No magic numbers** — use Tailwind spacing scale (`p-4`, `gap-2`, etc.)
3. **Consistent radius** — set `--radius: 0.5rem` in globals.css; use `rounded-lg` for cards, `rounded-md` for inputs
4. **Muted text** — secondary text uses `text-muted-foreground`, not `text-gray-500`
5. **Borders** — `border-border` not `border-gray-200`; keep borders subtle
6. **Icons** — always 16px (`size-4`) in text, 20px (`size-5`) standalone
7. **Loading** — `Skeleton` for content; `Loader2 className="animate-spin"` for buttons
8. **Empty states** — always provide an empty state with icon + headline + CTA
9. **Motion** — max 200ms duration for micro-interactions; 300ms for panel transitions
10. **Accessibility** — all icon buttons must have `aria-label`; all form inputs must have `label`
