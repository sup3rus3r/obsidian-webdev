# Contributing to Obsidian WebDev

Thank you for your interest in contributing to Obsidian WebDev! Whether you're fixing a bug, proposing a new feature, improving documentation, or triaging issues — every contribution is valued and appreciated.

Please take a moment to read these guidelines before getting started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Development Setup](#development-setup)
- [Branch & Commit Conventions](#branch--commit-conventions)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style & Standards](#code-style--standards)
- [Security Vulnerabilities](#security-vulnerabilities)
- [License](#license)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold a welcoming and respectful environment for everyone.

## Ways to Contribute

- **Bug reports** — Found something broken? Open an issue.
- **Feature requests** — Have an idea? Share it with the community.
- **Code contributions** — Fix bugs, implement features, improve performance.
- **Documentation** — Improve the README, add inline comments, write guides.
- **Testing** — Write tests, reproduce reported bugs, validate fixes.
- **Triage** — Help label and prioritize open issues.

## Reporting Bugs

Before opening a new issue, please search existing issues to avoid duplicates.

When filing a bug report, include:

- **A clear and descriptive title**
- **Steps to reproduce** the problem
- **Expected behavior** vs. **actual behavior**
- **Environment details**: OS, Python version, Node.js version, Docker version, browser (if frontend)
- **Relevant logs or error messages** (redact any secrets or API keys)
- **Screenshots or recordings** if applicable

Do not include API keys, passwords, vault contents, or other sensitive information in issues.

## Suggesting Features

Feature requests are welcome. To suggest a new feature:

1. Search existing issues to see if it has already been proposed.
2. Open a new issue with the label `enhancement`.
3. Describe the problem your feature solves and your proposed solution.
4. Provide any relevant examples, mockups, or references.

For large or breaking changes, please open an issue to discuss before submitting a PR — this avoids wasted effort if the direction doesn't align with the project roadmap.

## Development Setup

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 18+ |
| npm | 9+ |
| [uv](https://docs.astral.sh/uv/) | latest |
| Docker | 24+ |
| MongoDB | 6+ (local) or MongoDB Atlas |

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/obsidian-webdev.git
cd obsidian-webdev
```

### 2. Backend Setup

```bash
cd backend
uv sync
cp .env.example .env   # fill in MONGO_URL, JWT_SECRET_KEY, FERNET_MASTER_KEY
uv run uvicorn main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### 4. Start services (Qdrant)

```bash
# From project root
npm run services
```

### 5. Run Both Together

```bash
# From project root
npm run dev
```

- API → http://localhost:8000/docs
- Frontend → http://localhost:3000

### Linux: Docker socket permissions

```bash
sudo usermod -aG docker $USER
# Then log out and back in, or reboot
```

## Branch & Commit Conventions

### Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feature/` | New features or enhancements |
| `fix/` | Bug fixes |
| `docs/` | Documentation-only changes |
| `refactor/` | Code refactoring without behavior change |
| `test/` | Adding or updating tests |
| `chore/` | Maintenance, dependency updates, tooling |

Examples:
```
feature/obsidian-ai-provider
fix/terminal-scroll-behavior
docs/environment-variables
```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(agents): add obsidian-ai model provider wrapper
fix(terminal): preserve viewport on incoming data when scrolled up
docs(readme): update Linux Docker socket setup instructions
```

Keep the subject line under 72 characters.

## Submitting a Pull Request

1. **Ensure your branch is up to date** with `main` before opening a PR:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Keep PRs focused** — one logical change per PR.

3. **Test your changes** locally before submitting.

4. **Open the PR against `main`** with:
   - A clear title following the commit convention above
   - A description explaining what changed and why
   - References to any related issues (e.g., `Closes #42`)
   - Screenshots or recordings for UI changes

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] No secrets, API keys, or personal data are included
- [ ] Backend changes include appropriate error handling
- [ ] Frontend changes have been tested in the browser
- [ ] Documentation updated where necessary
- [ ] Commit history is clean and follows conventions

## Code Style & Standards

### Python (Backend)

- **Type hints** on all function signatures
- **Pydantic models** for all request/response schemas
- **Async/await** patterns consistent with FastAPI conventions
- Use `pathlib.Path` instead of string path concatenation
- No unused imports or dead code

### TypeScript / JavaScript (Frontend)

- **TypeScript** — avoid `any` types
- **Functional React components** with hooks
- **Tailwind CSS** utility classes — avoid inline styles
- Follow existing patterns in the codebase

### General

- Write self-documenting code; add comments only where logic is non-obvious
- Keep functions small and focused
- Do not introduce new dependencies without prior discussion

## Security Vulnerabilities

**Please do not report security vulnerabilities through public GitHub issues.**

See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

## License

By contributing to Obsidian WebDev, you agree that your contributions will be licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** — the same license that governs the project.

See [LICENSE](LICENSE) for full terms.

*Thank you for helping make Obsidian WebDev better!*
