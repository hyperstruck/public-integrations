# Hyperstruck Core integrations

Use **[Hyperstruck Core](https://hyperstruck.com)** from the AI tools you already use. This repository brings together **lightweight ways to adopt the platform** without shipping a heavy SDK: starting points you can copy into your project or publish internally.

Putting domain expertise, knowledge, and memory to work is what turns AI into **real business outcomes**. Core delivers **advanced reasoning** — structured plans, milestones, and steps that steer work toward clear goals. The approach is **grounded in evidence**, designed to be **safe, auditable, and secure**, and paired with **cognitive learning** so you get **quality over quantity**: less noise, more trust, and time back for your team.

**Practical learning** accumulates what works: from your organization, from operators, and from knowledge you provide. That learning **feeds the reasoning layer** — including resolving conflicting facts, applying lessons to future plans, and **improving over time**. You can **manage learnings yourself** (for example from an IDE) or rely on **automated** flows inside the platform.

---

## What is in this repository


| Path                                                               | What it is for                                                                                                                                                          |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [claude_skills/hyper-reasoning/](claude_skills/hyper-reasoning/) | **Hosted reasoning** from Claude Code or Cursor: send rich context, receive structured plans and analysis, handle review checkpoints when policies require it.          |
| [claude_skills/hyper-learning/](claude_skills/hyper-learning/)   | **Learnings API** from your agent: search before hard tasks, store insights after, reinforce what helped — so the platform remembers and ranks knowledge appropriately. |
| [claude_skills/hyper-plans/](claude_skills/hyper-plans/)         | **Plans API** from your agent: search similar plans and review candidate learnings surfaced with those results.                                                         |
| [hyperstruck-py/](hyperstruck-py/)                              | The hand-written **`hyperstruck`** Python package: a thin HTTP client plus an optional LangGraph middleware (the `langgraph` extra). The ergonomic learning surface, installed straight from this repository (see [hyperstruck-py/README.md](hyperstruck-py/README.md#install)), and your agent learns run over run. |
| [sdk/](sdk/)                                                    | Generated low-level API clients (Python and TypeScript) produced from the platform's OpenAPI schema. Raw, fully-typed access to every endpoint; prefer `hyperstruck-py` for the ergonomic learning surface, reach for these when you need an endpoint the package does not wrap. |


Together, these skills mirror how Core is meant to be used: **reason** when problems are deep or cross-cutting, **learn** continuously so the next session starts smarter.

Skill names use the **`hyper-` prefix** so they do not clash with third-party skills in a shared skills directory. See [claude_skills/README.md](claude_skills/README.md) for a short directory overview.

There are **no extra scripts or package dependencies**. Instructions tell your AI assistant how to call the **Hyperstruck HTTP API** using built-in capabilities (for example `curl` or `WebFetch`).

### Learning standing and corpus compatibility

The `utility` value returned in a learning's `standing` is Core's derived,
recency-weighted application-outcome score. It changes as later runs show that a
learning helped or misled an agent; it is not a confidence field or the
persistence source of truth. The optional `utility` accepted when manually
storing a learning is only its starting prior.

Core schema v5 is the required persistence and corpus-bundle contract. Normal
API and SDK users do not construct that internal payload: use the documented
learning request and response models instead. Platform-operated corpus export,
import, and clone validate the complete selected corpus or bundle before
producing output or writing data. A legacy or malformed learning therefore
fails the operation instead of yielding a partial bundle or partial import.
Existing operator-managed corpora must complete the global v4-to-v5 migration
before transfer.

---

## Getting started

### 1. Install the skills

Copy or symlink each skill folder into your environment’s skill directory:

```bash
# Claude Code
cp -r claude_skills/hyper-reasoning .claude/skills/
cp -r claude_skills/hyper-learning .claude/skills/
cp -r claude_skills/hyper-plans .claude/skills/

# Cursor (optional)
cp -r claude_skills/hyper-reasoning .cursor/skills/
cp -r claude_skills/hyper-learning .cursor/skills/
cp -r claude_skills/hyper-plans .cursor/skills/
```

> **Browsing inside the Hyperstruck Core Platform monorepo?** These paths live under `public_integrations/` (for example `public_integrations/claude_skills/hyper-reasoning`).

Each skill includes:

- **`SKILL.md`** — what the assistant reads on each invocation (including frontmatter where supported).
- **`reference.md`** — detailed request and response shapes when something more than the summary is needed.

### 2. Configure access

You need a **Hyperstruck API key** and (for learnings) usually an **agent id** that scopes stored knowledge.

**API key** (first match wins):

1. A key you paste in chat (never echoed back by the skill).
2. Environment variable **`HYPER_API_KEY`**.
3. A **`.env`** file in the project root, or a path pointed to by **`PUBLIC_INTEGRATIONS_ENV_FILE`**.

Send it on every request as:

`Authorization: Bearer <your key>`

**API base URL** — default **https://api.hyperstruck.com**. Override via conversation, **`HYPER_BASE_URL`**, or `.env`.

**Agent identity** — two env vars, two APIs:

| Variable | Used by | Value |
| -------- | ------- | ----- |
| **`HYPER_AGENT_NAME`** | Learning boundary (`POST /resolve`, `/observe`, `/reinforce`) and IDE hooks | Human-readable agent **name** (e.g. `support-bot`). If the name does not exist yet, the boundary **creates a learning agent with that name** on first use. |
| **`HYPER_AGENT_ID`** | REST skills (`GET/POST /agents/{agent_id}/...`) | Hosted agent **UUID** from `GET /agents` |

Do **not** paste a Postgres UUID into `HYPER_AGENT_NAME` — the boundary would create a separate stub agent *named* with that UUID and learnings would land in the wrong corpus.

For **`hyper-learning`** / **`hyper-reasoning`** / **`hyper-plans`** REST calls:

1. You specify the UUID explicitly, or
2. **`HYPER_AGENT_ID`** / `.env`, or
3. The skill lists available agents (`GET /agents?limit=50`) and asks you to pick.

For the **IDE learning hook loop** (after `python -m hyperstruck.ide.install`), set **`HYPER_AGENT_NAME`**. The installer writes both vars automatically when you have a single agent.

### 3. Invoke from your assistant

Examples (exact slash syntax depends on your host):

```
/hyper-reasoning Map out a migration plan with milestones and risks
/hyper-learning search retry backoff
/hyper-plans search onboarding workflow
/hyper-learning store
/hyper-learning reinforce <learning-id>
```

**`hyper-reasoning`** is marked **high effort** in its frontmatter: it selects an appropriate Hyperstruck profile, assembles context from your session, submits work to Core, **polls until completion**, and walks through **human-in-the-loop** steps when a run is suspended. The **first real API call** is `GET /agents?limit=50`, which validates credentials in the same round trip as loading profiles — no extra validation request.

**`hyper-learning`** pre-approves the same HTTP tools so searches and writes do not trigger a permission prompt on every call.

Both skills can inject **current environment hints** at load time (for example whether `HYPER_API_KEY` is set) where the host supports inline shell in the skill body.

---

## Learn more

- **Product and platform:** [hyperstruck.com](https://hyperstruck.com)
- **Skill index:** [claude_skills/README.md](claude_skills/README.md)

If you are extending or publishing this material from Hyperstruck’s private engineering repository, see the internal maintainer note in the platform repo: `docs/public-integrations-maintainers.md`.

Changes merged to `main` under `public_integrations/` are mirrored automatically to [hyperstruck/public-integrations](https://github.com/hyperstruck/public-integrations) by the `sync-public-integrations` GitHub Action.
