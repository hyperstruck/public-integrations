# Hyperstruck Core integrations

Use **[Hyperstruck Core](https://hyperstruck.com)** from the AI tools you already use. This repository brings together **lightweight ways to adopt the platform** without shipping a heavy SDK: starting points you can copy into your project or publish internally.

Putting domain expertise, knowledge, and memory to work is what turns AI into **real business outcomes**. Core delivers **advanced reasoning** — structured plans, milestones, and steps that steer work toward clear goals. The approach is **grounded in evidence**, designed to be **safe, auditable, and secure**, and paired with **cognitive learning** so you get **quality over quantity**: less noise, more trust, and time back for your team.

**Practical learning** accumulates what works: from your organization, from operators, and from knowledge you provide. That learning **feeds the reasoning layer** — including resolving conflicting facts, applying lessons to future plans, and **improving over time**. You can **manage learnings yourself** (for example from an IDE) or rely on **automated** flows inside the platform.

---

## What is in this repository

| Path | What it is for |
|------|----------------|
| [`claude_skills/hyper-reasoning/`](claude_skills/hyper-reasoning/) | **Hosted reasoning** from Claude Code or Cursor: send rich context, receive structured plans and analysis, handle review checkpoints when policies require it. |
| [`claude_skills/hyper-learning/`](claude_skills/hyper-learning/) | **Learnings API** from your agent: search before hard tasks, store insights after, reinforce what helped — so the platform remembers and ranks knowledge appropriately. |
| [`claude_skills/hyper-plans/`](claude_skills/hyper-plans/) | **Plans API** from your agent: search similar plans, inspect a full plan, and render mermaid visualizations of milestones and steps. |

Together, these skills mirror how Core is meant to be used: **reason** when problems are deep or cross-cutting, **learn** continuously so the next session starts smarter.

Skill names use the **`hyper-` prefix** so they do not clash with third-party skills in a shared skills directory. See [`claude_skills/README.md`](claude_skills/README.md) for a short directory overview.

There are **no extra scripts or package dependencies**. Instructions tell your AI assistant how to call the **Hyperstruck HTTP API** using built-in capabilities (for example `curl` or `WebFetch`).

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

**API base URL** — default **`https://api.core.hyperstruck.com`**. Override via conversation, **`HYPER_BASE_URL`**, or `.env`.

**Agent id** (for `hyper-learning`):

1. You specify it explicitly, or
2. **`HYPER_AGENT_ID`** / `.env`, or
3. The skill lists available agents and asks you to choose.

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
- **Skill index:** [`claude_skills/README.md`](claude_skills/README.md)

If you are extending or publishing this material from Hyperstruck’s private engineering repository, see the internal maintainer note in the platform repo: `docs/public-integrations-maintainers.md`.
