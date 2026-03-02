# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives security updates.

| Version | Supported |
| ------- | --------- |
| `main` (latest) | Yes |
| Older commits | No |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, please use [GitHub's private security advisory](../../security/advisories/new). This ensures your report remains confidential until a fix is available.

Include as much of the following as possible:

- A description of the vulnerability and its potential impact
- The component or area affected (e.g., authentication, vault encryption, Docker socket, agent tools, API)
- Step-by-step instructions to reproduce the issue
- Any proof-of-concept code or screenshots
- Suggested mitigations, if any

You will receive a response as quickly as possible. Please allow reasonable time to investigate and patch the issue before any public disclosure.

## Security Architecture

Obsidian WebDev handles sensitive data including AI provider API keys. Here is how it protects them:

- **Vault encryption** — API keys are encrypted with Fernet (AES-128-CBC + HMAC-SHA256). Each user's key is derived from a master key via PBKDF2 (100,000 iterations). Decrypted values are never sent to the frontend.
- **JWT authentication** — short-lived tokens (8h default), signed with a secret key
- **Container isolation** — project containers run with `cap_drop=ALL`, `no-new-privileges`, memory and CPU limits, and bridged networking
- **Docker socket** — access is controlled via the `docker` group on Linux. Only trusted users should be added to this group.
- **Rate limiting** — all API endpoints are rate-limited per user via SlowAPI

## Known Limitations (by design)

- The `docker` group grants effective root access on Linux. This is a Docker limitation, not a bug in Obsidian WebDev. Only run the backend as a trusted user.
- Project containers have internet access by default (needed for `npm install` / `pip install` during builds). This can be restricted via Docker network configuration if needed.
