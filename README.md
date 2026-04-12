# Public integrations

This folder holds **customer-facing** integration material for Hyperstruck. It is written so the contents can be copied into a **separate public repository** without leaking internal IP, proprietary implementation details, real endpoints beyond the documented default, customer data, or secrets.

## Warnings

> **This folder will be published publicly.** Review every change carefully.

- **Do not commit** API keys, tenant IDs, production agent IDs, internal hostnames, or private documentation into this tree.
- **Do not reference** internal code paths, private repos, or proprietary architecture.
- Skills are **instructions for an AI coding agent** — they guide HTTP calls but do not ship secrets or libraries.
- Assume downstream users will share snippets in public forums.

---

## What's here

| Path | Purpose |
|------|---------|
| `claude_skills/platform-agent-run/` | Skill for dispatching a Hyperstruck hosted agent goal from Claude Code, with OpenAPI discovery, agent listing, rich context assembly, run polling, and HITL resume. |
| `claude_skills/platform-learnings/` | Skill for manually managing learnings — store, search, get, and reinforce — without going through a full agent run. |

There are no scripts or library dependencies. The skills instruct the AI agent to make HTTP calls directly using whatever HTTP capability the host tool provides (Claude Code's `fetch`, `curl` in a shell, etc.). No `jq`, no specific Python version, no pip packages required.

---

## Installation

Copy or symlink each skill folder into your project's skill directory:

```bash
# Claude Code
cp -r public_integrations/claude_skills/platform-agent-run .claude/skills/
cp -r public_integrations/claude_skills/platform-learnings .claude/skills/

# Cursor (if using .cursor/skills)
cp -r public_integrations/claude_skills/platform-agent-run .cursor/skills/
cp -r public_integrations/claude_skills/platform-learnings .cursor/skills/
```

---

## Configuration

### API key

Both skills resolve the API key in this order (first match wins):

1. **Explicit** — key provided in the conversation (the skill will never echo it back).
2. **Environment variable** — `HYPER_API_KEY`.
3. **Dotenv file** — `.env` in the project root, or a path from `PUBLIC_INTEGRATIONS_ENV_FILE`. Expected format: `HYPER_API_KEY=<value>`.

If none found, the skill stops and asks the user to configure one.

Send the key as: `Authorization: Bearer <key>`.

### Base URL

Default: **`https://api.core.hyperstruck.com`**

Override with (first match wins):
1. Explicit user instruction in the conversation.
2. `HYPER_BASE_URL` environment variable.
3. `.env` file: `HYPER_BASE_URL=https://your-custom-host`.

### Agent ID (for learnings skill)

The learnings skill needs an agent ID to scope operations. It resolves via:
1. Explicit user-provided value.
2. `HYPER_AGENT_ID` env var or `.env` entry.
3. Falls back to listing agents via the API and asking the user to choose.

---

## Skill details

### platform-agent-run

**When to use:** Your current Claude Code task would benefit from deeper reasoning, multi-step planning, or cross-domain analysis by a hosted agent. The skill will **not** invoke itself for simple edits or lookups.

**What it does:**

1. Optionally fetches `GET /openapi.json` to discover or confirm endpoints.
2. Lists your agents (`GET /agents`) and checks if any match the current task by name/description. **Exits early** if no suitable agent exists.
3. Builds a **rich context block** from the current session: task background, work done so far, data from integrations, discovered pitfalls, open questions, constraints.
4. Dispatches `POST /agents/{agent_id}/goals` with the structured goal and context.
5. Polls `GET /runs/{run_id}` with progressive backoff (3s → 5s → 10s, max 10 min).
6. Handles `suspended` status by presenting the HITL gate to the user and sending `POST /runs/{run_id}/resume`.
7. Returns the run output for you to integrate into the current task.

### platform-learnings

**When to use:** You want to store insights from local work, recall relevant knowledge before a task, or give feedback on past learnings — all without dispatching a full agent run.

**What it does:**

- **Search** (`GET .../learnings/search?q=...`) — find relevant existing learnings.
- **Get** (`GET .../learnings/{id}`) — full record for a search hit.
- **Store** (`POST .../learnings`) — persist a new learning (async 202; wait before searching).
- **Reinforce** (`POST .../learnings/{id}/reinforce`) — mark helpful/unhelpful to tune confidence and trust.

---

## Contributing

- Prefer placeholders (`https://your-api-host`, `<your-agent-id>`) over real values in examples.
- Keep skills self-contained — each `SKILL.md` must work without the other.
- No external dependencies: the skills use only the host agent's built-in HTTP and JSON capabilities.
