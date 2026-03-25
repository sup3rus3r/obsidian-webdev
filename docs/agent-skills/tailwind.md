# Tailwind CSS v4 Skill — Obsidian WebDev Agent

This skill applies to ALL JavaScript/TypeScript projects (Next.js, React/Vite, Fullstack).

---

## Critical: Tailwind v4 is a breaking change from v3

Tailwind CSS v4 is fundamentally different from v3. Do NOT use v3 patterns.

### What changed

| v3 (OLD — do not use) | v4 (correct) |
|---|---|
| `tailwind.config.js` | Config lives in CSS via `@theme` |
| `@tailwind base;` | `@import "tailwindcss"` |
| `@tailwind components;` | Removed |
| `@tailwind utilities;` | Removed |
| `theme.extend.colors` in JS | `--color-*` CSS variables in `@theme` |
| `darkMode: 'class'` in config | `@variant dark` in CSS |
| `content: [...]` paths | Auto-detected — no config needed |
| `theme()` function in CSS | `var(--color-*)` CSS variables |
| JIT mode | Always on, no config needed |

---

## Correct v4 setup

### CSS entry file (globals.css or main.css)

```css
@import "tailwindcss";

@theme {
  /* Custom colors */
  --color-brand: #6366f1;
  --color-brand-dark: #4f46e5;

  /* Custom fonts */
  --font-sans: "Inter", ui-sans-serif, system-ui;

  /* Custom spacing */
  --spacing-18: 4.5rem;

  /* Custom breakpoints */
  --breakpoint-xs: 475px;
}
```

### Checking the existing config

**ALWAYS** read the project's CSS entry file before adding custom tokens:
```
read_file("src/app/globals.css")   # Next.js
read_file("src/index.css")         # React/Vite
```

---

## Using utilities

All standard Tailwind utilities work the same way as v3 in JSX/HTML:

```tsx
<div className="flex items-center gap-4 p-6 rounded-xl bg-white shadow-md">
  <h1 className="text-2xl font-bold text-gray-900">Title</h1>
  <p className="text-sm text-gray-500">Subtitle</p>
</div>
```

### Responsive design (unchanged from v3)

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
```

### Dark mode in v4

```css
/* In globals.css */
@variant dark (&:where(.dark, .dark *));
```

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
```

### Arbitrary values (unchanged)

```tsx
<div className="w-[320px] bg-[#ff6b6b] mt-[13px]">
```

---

## Custom theme tokens — how to access in JSX

Custom tokens defined in `@theme` become CSS variables automatically:

```css
@theme {
  --color-brand: #6366f1;
}
```

```tsx
{/* Use as a Tailwind utility */}
<button className="bg-brand text-white hover:bg-brand-dark">
```

```tsx
{/* Or as inline style */}
<div style={{ color: 'var(--color-brand)' }}>
```

---

## Installing Tailwind v4

If not already installed:
```bash
npm install tailwindcss@^4 @tailwindcss/postcss@^4
```

`postcss.config.mjs`:
```js
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

Verify install:
```bash
npm run build 2>&1 | tail -5
```

---

## What NOT to do

- Never create or modify `tailwind.config.js` or `tailwind.config.ts` — v4 does not use it
- Never write `@tailwind base;` / `@tailwind components;` / `@tailwind utilities;`
- Never use `theme()` function in CSS — use `var(--color-*)` instead
- Never add `content: [...]` array — v4 auto-detects template files
- Never install `@tailwindcss/jit` — always on in v4
- Never use `purge` config option — removed in v4

---

## Context7 — fetch before using any utility you are unsure about

```
GET https://context7.com/api/v1/tailwindlabs/tailwindcss.com?tokens=6000&topic=<TOPIC>
```

| What you need | Topic |
|---|---|
| v4 migration / setup | `upgrade-guide` |
| Theme customization | `theme` |
| Colors system | `colors` |
| Typography utilities | `typography` |
| Flexbox utilities | `flexbox` |
| Grid utilities | `grid` |
| Spacing and sizing | `spacing` |
| Responsive design | `responsive-design` |
| Dark mode | `dark-mode` |
| Arbitrary values | `arbitrary-values` |
| Animations | `animation` |
| Custom variants | `adding-custom-styles` |
| CSS variables | `using-css-variables` |

**Call example:**
```
web_fetch("https://context7.com/api/v1/tailwindlabs/tailwindcss.com?tokens=6000&topic=upgrade-guide")
```

Always fetch when:
- Using a utility added or changed in v4 (especially `@theme`, `@variant`, `@import`)
- Unsure if a pattern from v3 still works
- Setting up Tailwind in a new project
