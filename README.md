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
| `claude_skills/platform-agent-run/` | Skill for dispatching a Hyperstruck hosted agent goal from Claude Code — with OpenAPI discovery, agent listing, rich context assembly, run polling, and HITL resume. |
| `claude_skills/platform-learnings/` | Skill for manually managing learnings — store, search, get, and reinforce — without a full agent run. |

No scripts, no library dependencies. The skills instruct the AI agent to make HTTP calls directly using whatever capability the host tool provides (`curl`, `WebFetch`, etc.).

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

Each skill folder includes:
- `SKILL.md` — main instructions with frontmatter configuration.
- `reference.md` — full API endpoint schemas loaded on demand (keeps `SKILL.md` lean).

---

## Configuration

### API key

Both skills resolve the API key in this order (first match wins):

1. **Explicit** — key provided in the conversation (the skill will never echo it back).
2. **Environment variable** — `HYPER_API_KEY`.
3. **Dotenv file** — `.env` in the project root, or a path from `PUBLIC_INTEGRATIONS_ENV_FILE`.

If none found, the skill stops and asks the user to configure one.

Send the key as: `Authorization: Bearer <key>`.

### Base URL

Default: **`https://api.core.hyperstruck.com`**

Override with (first match wins):
1. Explicit user instruction in the conversation.
2. `HYPER_BASE_URL` environment variable.
3. `.env` file: `HYPER_BASE_URL=https://your-custom-host`.

### Agent ID (for learnings)

The learnings skill needs an agent ID to scope operations. It resolves via:
1. Explicit user-provided value.
2. `HYPER_AGENT_ID` env var or `.env` entry.
3. Falls back to listing agents via the API and asking the user to choose.

---

## Claude Code-specific features

These skills leverage several Claude Code capabilities for a better experience:

### Dynamic context injection (`!` `` syntax)

Both skills auto-resolve `HYPER_BASE_URL`, `HYPER_AGENT_ID`, and `HYPER_API_KEY` presence **at skill load time** using inline shell commands. The agent sees the resolved values immediately — no guessing needed.

### Argument support

Invoke skills with arguments:

```
/platform-agent-run Analyze the performance bottleneck in the payment flow
/platform-learnings retry backoff strategies
/platform-learnings store
/platform-learnings reinforce <learning-id>
```

The `argument-hint` frontmatter shows expected args in the `/` menu.

### Pre-approved tools (`allowed-tools`)

Both skills pre-approve `Bash(curl *)` and `WebFetch` so the agent can make API calls and poll runs without prompting for permission on each request.

### Effort level

`platform-agent-run` sets `effort: high` because it involves multi-step reasoning: agent selection, context assembly, goal dispatch, and iterative polling.

### One-time API key validation (hooks)

`platform-agent-run` includes a `PreToolUse` hook with `once: true` that validates the API key against the Hyperstruck API on first use. If the key is invalid, the hook denies the tool call with a clear error instead of letting the agent hit auth failures mid-flow.

### Supporting files

Each skill separates concerns:
- `SKILL.md` — concise instructions (what the agent reads on every invocation).
- `reference.md` — full endpoint schemas, error codes, response shapes (loaded on demand via `[reference.md](reference.md)` link when the agent needs details).

This keeps context usage low on typical invocations while providing deep reference when needed.

---

## Skill details

### platform-agent-run

**When to use:** The current task would benefit from deeper reasoning, multi-step planning, or cross-domain analysis by a hosted agent. The skill explicitly guards against invocation for simple tasks.

**Flow:**
1. Resolves config (env vars auto-detected at load time).
2. Fetches `GET /openapi.json` to discover/confirm endpoints.
3. Lists agents and matches by name/description — **exits early** if none fit.
4. Builds **rich context** from the current session (background, integration data, pitfalls, open questions, constraints).
5. Dispatches `POST /agents/{id}/goals` with structured goal + context.
6. Polls `GET /runs/{id}` with progressive backoff (3s → 5s → 10s, max 10 min).
7. Handles `suspended` / HITL resume via `POST /runs/{id}/resume`.
8. Returns output for integration into the current task.

### platform-learnings

**When to use:** Store insights from local work, recall relevant knowledge before a task, or give feedback on past learnings — all without dispatching a full agent run.

**Operations:**
- **Search** (`GET .../learnings/search?q=...`) — find relevant existing learnings.
- **Get** (`GET .../learnings/{id}`) — full record for a search hit.
- **Store** (`POST .../learnings`) — persist a new learning (async 202; wait before searching).
- **Reinforce** (`POST .../learnings/{id}/reinforce`) — mark helpful/unhelpful.

---

## Contributing

- Prefer placeholders (`https://your-api-host`, `<your-agent-id>`) over real values in examples.
- Keep skills self-contained — each `SKILL.md` must work without the other.
- No external dependencies: the skills use the host agent's built-in HTTP and JSON capabilities.
- Test changes by installing into a `.claude/skills/` directory and invoking from a live Claude Code session.
