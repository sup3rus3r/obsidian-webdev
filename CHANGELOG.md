# Changelog

All notable changes to Obsidian WebDev will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- obsidian-ai model provider integration (session-based SSE wrapper)
- Orchestrator mandatory research phase — web search for current library versions before building
- Docker Compose for full local dev stack
- Container idle cleanup job (auto-stop after 30 min, remove after 48h)
- Production PostgreSQL backend (AsyncPostgresSaver + AsyncPostgresStore)

---

## [1.0.0] — 2026-03-01

Initial public release.

### Added

**Core Platform**
- Multi-agent build system powered by LangGraph 1.0
- Agent graph: Clarifier → Orchestrator → [Frontend | Backend | DevOps | QA] → BuildValidator → ErrorAnalyst
- Human-in-the-loop clarification phase — agents batch all questions before building
- Pre-build conversation mode (assistant agent) — refine requirements before triggering a build
- Web search tools for agents (Tavily primary, DuckDuckGo fallback)
- Semantic codebase indexing via Qdrant — agents find relevant files without loading everything

**Model Providers**
- Anthropic (Claude Opus 4.6, Sonnet 4.6, Haiku 4.5)
- OpenAI (GPT-4.1, GPT-4.1-mini, o3, o4-mini)
- Ollama (any local model via OpenAI-compatible API)
- LMStudio (local model server)

**Docker Container Execution**
- Per-project isolated Docker containers with volume-mounted workspace
- Multi-port mapping (3000, 5173, 8000) with dynamic host port assignment
- TCP probe preview auto-detection — no manual port configuration needed
- tmux sessions — terminal processes survive WebSocket disconnects
- Auto-start container on workspace load
- Container files persisted to MongoDB — container loss never means data loss

**Browser IDE Workspace**
- Monaco editor with multi-tab support, dirty state tracking, syntax highlighting
- Live file tree with real-time updates from agent file writes
- xterm.js terminal with smart scroll (preserves viewport when scrolled up)
- Preview iframe with auto TCP probe and 5s polling
- Agent chat panel — streaming tokens, tool calls, HITL questions, file write events
- File attachments in chat — PDF text extraction, image base64, plain text

**Project Management**
- Project CRUD with framework picker (React SPA, Next.js, FastAPI, Fullstack)
- Run / Stop container controls
- Export project as ZIP (all source files, browser download)
- Download individual files from Monaco editor
- Create files manually from file tree
- Collapsible file tree sidebar
- Project deletion with full cleanup (container, Qdrant index, MongoDB, localStorage)

**Security & Auth**
- JWT authentication (NextAuth v5 frontend, FastAPI backend)
- Fernet vault — PBKDF2 per-user derived keys, encrypted at rest
- API keys never sent to frontend; injected server-side only
- Per-container resource limits and capability restrictions

**Chat & Session Persistence**
- Chat history, session state, and conversation history persisted to localStorage per project
- Session restore on workspace reload — reconnects to previous agent session
- Build proposal card — assistant proposes architecture before triggering build

[Unreleased]: https://github.com/your-org/obsidian-webdev/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/obsidian-webdev/releases/tag/v1.0.0
