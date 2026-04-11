# Public integrations

This folder holds **customer-facing** integration material (Claude Code skills, small helpers, and usage notes). It is written so the contents can be copied into a **separate public repository** without leaking internal intellectual property, proprietary product names beyond what you intentionally export, real endpoints beyond placeholders, customer data, or secrets.

## Warnings

- **Do not commit API keys**, tenant IDs, agent IDs from production, internal hostnames, or private documentation into this tree.
- **Review every change** before publishing: assume downstream users will share snippets in public forums.
- Skills are **instructions for an AI agent**; they do not perform authentication by themselves. The human still supplies credentials through environment variables or explicit context.

## Layout

| Path | Purpose |
|------|---------|
| `claude_skills/` | Skill folders (`SKILL.md` per skill). Install by copying or symlinking into your project's `.claude/skills/` (or your tool's equivalent). |
| `scripts/` | Optional, dependency-light helpers (stdlib only) to call the HTTP API with consistent auth and run polling. |

## Configuration

### Base URL and agent

Set the API host and target agent explicitly (values are yours; do not hardcode secrets here):

- `HYPER_BASE_URL` — e.g. `https://api.example.com` (no trailing slash required)
- `HYPER_AGENT_ID` — UUID of the agent to run goals and learnings against

### API key resolution order

Integrations use this order unless a skill says otherwise:

1. **Explicit** — API key passed in the user message or tool invocation (avoid logging it).
2. **Environment** — `HYPER_API_KEY` (recommended for local dev).
3. **Dotenv file** — `.env` in the current working directory, or a path from `PUBLIC_INTEGRATIONS_ENV_FILE`. Expected line format: `HYPER_API_KEY=...` (and optionally `HYPER_BASE_URL`, `HYPER_AGENT_ID`).
4. If still missing, **stop** and ask the human to set one of the above.

Send the key as: `Authorization: Bearer <full-key>`.

### Optional: Python helper

From the repository root (or any path; adjust `PYTHONPATH` if you vendor the script):

```bash
export HYPER_BASE_URL="https://your-api-host"
export HYPER_AGENT_ID="your-agent-uuid"
export HYPER_API_KEY="your-key"   # or use .env

# Dispatch a goal and poll until terminal (default interval 2s, max 120s)
python public_integrations/scripts/platform_api_client.py goal-run \
  --goal "Your objective text" \
  --context "Optional structured context"

# Poll an existing run
python public_integrations/scripts/platform_api_client.py poll-run --run-id "<run-uuid>"

# Search learnings (URL-encode queries with spaces as + or %20)
python public_integrations/scripts/platform_api_client.py learnings-search --query "retry strategy"

# Queue a learning (HTTP 202 — wait before expecting search to find it)
python public_integrations/scripts/platform_api_client.py learnings-store \
  --content "Short actionable learning text" \
  --learning-type pitfall
```

Use `python public_integrations/scripts/platform_api_client.py --help` for subcommands.

**Stdout safety:** the script prints full JSON response bodies. Treat terminal output as potentially sensitive (user content, internal errors). Redirect to a file or pipe through a redactor if you share logs.

## Claude skills (per-integration usage)

Install skills so your coding agent can load them (example: copy each `claude_skills/<name>/` folder into `.claude/skills/`).

| Skill folder | When to use |
|--------------|-------------|
| `platform-context-handoff` | **First** — shapes what context the agent must collect (goal summary, prior learnings, tools, constraints) before calling the platform. |
| `platform-agent-run` | Dispatch **POST** `/agents/{id}/goals`, poll **GET** `/runs/{id}`, handle **suspended** / **POST** `/runs/{id}/resume`, optional continuation on same session. |
| `platform-agent-run-curl` | Same outcomes as above using **curl** only (no Python). |
| `platform-learnings` | **POST** learnings (async 202), **search**, **get**, **reinforce**; reminds about indexing delay. |
| `platform-learnings-recall` | Read-heavy path: search + get before work; reinforce after. |
| `platform-cognitive-loop` | End-to-end: handoff → recall learnings → platform goal run → store new learnings. |

Each `SKILL.md` includes endpoint paths aligned with public flow docs: session lifecycle (goals, runs, resume, sessions) and learnings lifecycle (store, search, get, reinforce).

## Relationship to platform docs

Your deployment may ship detailed curl flows (for example under `docs/flows/` in a private repo). This folder stays **generic**: it references standard REST paths and behavior (polling, 202 on learning store, 409 on conflicting session runs) without copying proprietary internals.

## Contributing here

- Prefer placeholders over real URLs.
- Redact examples in commit messages and tickets.
- Keep scripts stdlib-only unless there is a strong reason to add dependencies.
