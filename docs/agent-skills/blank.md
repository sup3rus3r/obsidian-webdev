# Blank Project Skill — Obsidian WebDev Agent

You are working on a **blank project** inside `/workspace`. No framework has been pre-scaffolded. Follow these rules.

---

## Step 1 — Understand what exists before doing anything

```
list_files_brief("/workspace")
```

A blank project may be:
- Truly empty (just initialized)
- A git-cloned repo that you need to understand
- A partially built project the user is continuing

Read any `README.md`, `package.json`, `pyproject.toml`, or `Cargo.toml` present before writing a single line of code.

---

## Step 2 — If the user wants you to scaffold, ask what they want

Use `ask_user` once to clarify:
- What language/framework do they want?
- What is the project's purpose?

Then scaffold based on their answer using the appropriate skill rules below.

---

## Scaffolding by technology

### Node.js / TypeScript project
```bash
npm init -y
npm install typescript @types/node tsx
npx tsc --init
```

### React + Vite
```bash
npm create vite@latest . -- --template react-ts
npm install
```
Then apply **react.md** rules.

### Next.js
```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git --yes
npm install
```
Then apply **nextjs.md** rules.

### FastAPI
```bash
uv init
uv add fastapi[standard] uvicorn[standard] pydantic-settings
```
Then apply **fastapi.md** rules.

### Express + TypeScript
```bash
npm init -y
npm install express cors helmet
npm install -D typescript @types/node @types/express tsx
npx tsc --init
```

---

## Context7 — fetch docs for whatever you are building

Identify the technology and use the right Context7 endpoint:

```
# Next.js
web_fetch("https://context7.com/api/v1/nextjs/nextjs/docs?tokens=8000&topic=<TOPIC>")

# React
web_fetch("https://context7.com/api/v1/facebook/react/docs?tokens=8000&topic=<TOPIC>")

# FastAPI
web_fetch("https://context7.com/api/v1/tiangolo/fastapi/docs?tokens=8000&topic=<TOPIC>")

# Express
web_fetch("https://context7.com/api/v1/expressjs/express/docs?tokens=6000&topic=<TOPIC>")

# Tailwind v4
web_fetch("https://context7.com/api/v1/tailwindlabs/tailwindcss/docs?tokens=6000&topic=<TOPIC>")

# TypeScript
web_fetch("https://context7.com/api/v1/microsoft/typescript/docs?tokens=6000&topic=<TOPIC>")
```

---

## General rules for any project in a blank container

- Port **3000** is the default host-mapped port — configure your server to listen on 3000 unless the user specifies otherwise
- Always run build/start commands to verify the project works
- Check what's already installed before installing anything
- Commit after scaffolding: `git init && git add -A && git commit -m "initial scaffold"`

---

## Git integration

SSH key is pre-injected:
```bash
git init
git remote add origin <url>
git add -A && git commit -m "initial commit"
git push -u origin main
```
