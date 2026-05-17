# Security Policy

Goalcast is a personal/small-team project. We do not run a paid bug bounty, but
we take credible reports seriously and will respond.

## Supported versions

Only the current `master` branch is supported. `v2` is an active rewrite —
fixes land on the branch and graduate to `master` via PR.

## Reporting a vulnerability

**Do not open a public GitHub issue for a vulnerability.**

Email the maintainer (see the commit log for `git config user.email`) with:

1. A description of the issue and its impact.
2. Reproduction steps, ideally a minimal failing input or request.
3. Affected code path or endpoint.
4. Whether you intend to disclose publicly, and on what timeline.

Expect an acknowledgement within 5 business days. We will work with you on a
fix and a coordinated disclosure window proportional to severity (typically
≤ 30 days for high-severity, ≤ 90 days for medium).

## In scope

- The FastAPI backend (`backend/`) — auth, input validation, SQL/HTTP injection,
  SSRF against the OddAlerts proxy path, secret leakage in logs/responses.
- The React frontend (`frontend/`) — XSS via odds/team-name rendering,
  open-redirect, exposed environment variables in the bundle.
- The sync pipeline (`backend/services/sync.py`) — anything that could be
  triggered via a malformed upstream OddAlerts response.
- Local SQLite handling (`backend/database.py`) — the WAL setup and
  concurrent-write guarantees.

## Out of scope

- DoS via raw request volume against a self-hosted instance.
- Findings that require a malicious upstream OddAlerts API (we treat them as
  trusted for this project's threat model).
- Social engineering against maintainers or contributors.
- Issues that only apply to forks with custom changes.

## Secrets handling

- `.env` files are gitignored (`.gitignore:2`). Do not commit API keys, tokens,
  or credentials. If you ever do, rotate the key first, then remove the file
  from history.
- The OddAlerts API key is the only credential the backend uses today. It is
  loaded via `pydantic-settings` from environment variables (see
  `backend/config.py`).

## Dependencies

Automated dependency updates are configured in `.github/dependabot.yml` for
pip (backend), npm (frontend), and GitHub Actions. Review and merge security
updates promptly; treat any `severity: high` or `severity: critical` advisory
as a release blocker.
