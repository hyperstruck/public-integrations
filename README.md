# Hyperstruck Core integrations

Use **[Hyperstruck Core](https://hyperstruck.com)** from the AI tools you already use. This repository brings together **lightweight ways to adopt the platform** without shipping a heavy SDK: starting points you can copy into your project or publish internally.

Putting domain expertise, knowledge, and memory to work is what turns AI into **real business outcomes**. Core delivers **advanced reasoning** — structured plans, milestones, and steps that steer work toward clear goals. The approach is **grounded in evidence**, designed to be **safe, auditable, and secure**, and paired with **cognitive learning** so you get **quality over quantity**: less noise, more trust, and time back for your team.

**Practical learning** accumulates what works: from your organization, from operators, and from knowledge you provide. That learning **feeds the reasoning layer** — including resolving conflicting facts, applying lessons to future plans, and **improving over time**. You can **manage learnings yourself** (for example from an IDE) or rely on **automated** flows inside the platform.

---

## What is in this repository


| Path                                                               | What it is for                                                                                                                                                          |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [claude_skills/hyper-learning/](claude_skills/hyper-learning/)   | **Learnings API** from Claude Code, Cursor, or Claude CoWork: search before hard tasks, store insights after, reinforce what helped — so the platform remembers and ranks knowledge appropriately. |
| [claude_skills/hyper-workflows/](claude_skills/hyper-workflows/) | **Workflows** from your agent: find the saved workflow that fits a task (with what its agents learned), run it, or draft and save a new one. |
| [hyperstruck-py/](hyperstruck-py/)                              | The hand-written **`hyperstruck`** Python package: a thin HTTP client plus an optional LangGraph middleware (the `langgraph` extra). The ergonomic learning surface, installed straight from this repository (see [hyperstruck-py/README.md](hyperstruck-py/README.md#install)), and your agent learns run over run. |
| [openapi.json](openapi.json)                                    | The published OpenAPI document. It lives here as a file because no deployment serves `/openapi.json`: the interactive docs and the schema route are mounted only in local development, so this file is the machine-readable contract. |
| `.mcp.json`, `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`, `assets/logo.svg` | Marketplace-ready plugin manifests for the hosted MCP server at `https://mcp.hyperstruck.com/mcp`. Sign-in is WorkOS AuthKit OAuth; directory submission is a follow-up. |

Together, these skills mirror how Core is meant to be used: **reason** when problems are deep or cross-cutting, **learn** continuously so the next session starts smarter.

Skill names use the **`hyper-` prefix** so they do not clash with third-party skills in a shared skills directory. See [claude_skills/README.md](claude_skills/README.md) for a short directory overview.

There are **no extra scripts or package dependencies**. Instructions tell your AI assistant how to call the **Hyperstruck HTTP API** using built-in capabilities (for example `curl` or `WebFetch`).

### The OpenAPI document, and what publishing it does and does not close

`openapi.json` here **is** the contract: no deployed environment serves
`/openapi.json`, `/docs` or `/redoc`, so this file is where the schema lives.

Be clear about what that buys, because the file is published rather than hidden.
This repository is a public mirror, so the API surface it describes is
world-readable and stays so. What closing the served routes removes is the
interactive documentation UI on every deployed host, and with it the unescaped
HTML that the configurable docs paths were interpolated into. It is not schema
confidentiality, and nothing here should be read as offering it. Endpoints that
must not be enumerated are kept out of the schema entirely with
`include_in_schema=False`, which is a separate mechanism and the one that
actually hides a surface.

#### Regenerating it

A contract test pins this file to the schema the app builds, so any change to the
API surface fails CI until it is refreshed. Run it under `HYPER_ENV=dev`: on a
local checkout without its own Qdrant lane, building the app otherwise raises
`RuntimeError`, and the document is byte-identical under `dev`:

```bash
HYPER_ENV=dev uv run python -c "
import json
from api.main import create_app
with open('public_integrations/openapi.json', 'w') as f:
    json.dump(create_app().openapi(), f, indent=2, sort_keys=True)
    f.write('\n')
"
```

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

The same skills run in two different ways. Pick the path that matches the host:

```
Claude Code / Cursor                         Claude CoWork
--------------------                         -------------
hyperstruck.ide.install  -->  hooks + skills zip skill  -->  CoWork Skills Add
hooks own resolve / observe / reinforce      skill curls POST /resolve
                                             then POST /reinforce or /decline
```

`python -m hyperstruck.ide.install` deep-merges learning hooks into Claude Code and Cursor only. It does **not** install or wire Claude CoWork.

### 1. Install the skills

#### Claude Code and Cursor

Copy or symlink each skill folder into your environment’s skill directory:

```bash
# Claude Code
cp -r claude_skills/hyper-learning .claude/skills/
cp -r claude_skills/hyper-workflows .claude/skills/

# Cursor (optional)
cp -r claude_skills/hyper-learning .cursor/skills/
cp -r claude_skills/hyper-workflows .cursor/skills/
```

Or install [`hyperstruck-py`](hyperstruck-py/) and run `python -m hyperstruck.ide.install`. That command deep-merges learning hooks into Claude Code and Cursor and copies the bundled `hyper-*` skills without overwriting your existing hook entries. Restart the editor afterwards.

> **Browsing inside the Hyperstruck Core Platform monorepo?** These paths live under `public_integrations/` (for example `public_integrations/claude_skills/hyper-learning`).

Each skill includes:

- **`SKILL.md`** — what the assistant reads on each invocation (including frontmatter where supported).
- **Contract questions:** `hyper-learning` resolves contract questions against the published [`openapi.json`](https://github.com/hyperstruck/public-integrations/blob/main/openapi.json) at the repo root, so its instructions never drift from the API.

#### Claude CoWork

[Claude CoWork](https://claude.com/product/cowork) is a hosted teammate session, not a hooked editor. Add the **portable** `hyper-learning` skill from this repository (`SKILL.md` at the folder root). Do not use the IDE installer for CoWork, and do not treat a durable `~/.hyperstruck/venv` as proof that CoWork owns the live loop.

1. Zip the skill so the archive contains the folder wrapper (`hyper-learning/SKILL.md`), not a bare `SKILL.md` at the zip root:

   ```bash
   cd claude_skills
   zip -r hyper-learning.zip hyper-learning
   ```

   In this monorepo, start from `public_integrations/claude_skills`.

2. In CoWork, open **Customize → Skills** (some sessions also expose **+ → Skills → Add**) and **Upload a skill**. Choose `hyper-learning.zip` or the `hyper-learning/` folder. Enable the skill afterwards. Do not use account Settings, and do not use **Record a skill**.
3. Start a **new** CoWork session so the uploaded skill is loaded. CoWork and cloud sessions do not read `~/.claude/skills/` from your Mac.
4. On Team or Enterprise plans, publish the skill to the **team skill directory** (or have an admin provision it) if the rest of the org should see it.
5. Allowlist **`api.hyperstruck.com`** for CoWork network egress so `curl` from the sandbox can reach the Learnings API. In **Settings** (or **Organization settings** on Team/Enterprise) open **Capabilities → Code execution → Allow network egress** and add `api.hyperstruck.com` under **Additional allowed domains**. If you set `HYPER_BASE_URL` to another host, allowlist that host too. Start a **new** CoWork session after changing egress — an already-open session keeps the old policy. A `403` with `blocked-by-allowlist` or `host_not_allowed` means the host is missing from the allowlist or the session predates the change.

##### Advanced: add Hyperstruck MCP in CoWork

The skill path above is the portable install. If your CoWork workspace also lets you configure MCP servers, add Hyperstruck's hosted MCP endpoint so Claude can use managed tools instead of hand-written `curl` for the same learning loop and manual inspection tasks.

1. Open CoWork **Advanced settings** / **MCP server configuration**.
2. Add this server, replacing only the API key:

   ```json
   {
     "mcpServers": {
       "hyperstruck": {
         "url": "https://mcp.hyperstruck.com/mcp/",
         "headers": {
           "Authorization": "Bearer your-hyperstruck-api-key"
         }
       }
     }
   }
   ```

   Leave **`X-Hyperstruck-Agent-Name` unset** unless you want to pin `resolve` / `complete_run` / `distill` to one agent name. When the header is absent, hosted MCP uses the shared `default` agent namespace. To pin:

   ```json
   "X-Hyperstruck-Agent-Name": "support-bot"
   ```

   For manual learning and claim tools, call `list_agents` first. That lists the agents this caller can access so you can pick the right agent UUID and pull the correct learnings.

3. Allowlist **`mcp.hyperstruck.com`** for CoWork MCP / web-tool egress. Keep **`api.hyperstruck.com`** allowlisted too if you also use the skill's `curl` fallback.
4. Start a **new** CoWork session.

The API key must be active. `agents:read` is enough for `resolve`, `list_agents`, `list_learnings`, `search_learnings`, and `get_learning`. Add `agents:write` for `complete_run`, `distill`, `store_learning`, and `reinforce_learning`. Add `claims:read` for claim inspection tools.

The hosted MCP server currently exposes:

- `resolve` and `complete_run` for the automatic learning loop. `resolve` returns advice (`injected_text`), claim facts (`injected_facts_text`) and `has_reported_outcomes`, which stays false until the host reports a run's outcome, and until then no learning can be recommended. Always close with `complete_run`, including empty recalls.
- `distill` to extract learnings from a document, diff, or post-mortem that still needs contrast-based extraction. `store_learning` when you already have the final learning text. Do not swap those two.
- `list_agents`, `list_learnings`, `search_learnings`, `get_learning`, and `reinforce_learning` for manual learning work on a hosted agent UUID from `list_agents`.
- `list_learning_claims`, `get_claim_review_context`, `get_claim_entity`, and `get_claim_attribute` for claim inspection.
- `compile_watched_page`, `set_watched_page`, `list_watched_pages`, `update_watched_page`, `delete_watched_page`, `run_watched_page`, `stop_watched_page`, and `list_watched_page_runs` to keep a hosted agent current with a URL on a cadence (`15m`, `1h`, `6h`, `daily`, `weekly`). Reads need `agents:read`; the rest need `agents:write`. Deleting or stopping a watch keeps the documents it already uploaded.
- `list_insights`, `get_insight`, `create_insight`, `update_insight`, `delete_insight`, `refine_insight`, `run_insight`, `list_insight_runs`, `get_insight_run_events`, `list_insight_findings`, and `update_insight_finding` for insights (saved objectives asked across several agents, whose runs write cited findings). They need the account's insights feature and `claims:read`, plus `agents:read`, `agents:write`, or `agents:execute` (for `run_insight`). Runs are held against the account's spend limit.
- `list_workflows`, `get_workflow`, `run_workflow`, `get_workflow_run`, `draft_workflow`, and `save_workflow` for workflows (saved request-to-answer graphs with evals). `list_workflows` with a `goal` ranks workflows by fit. `include_context` defaults false; `include_context=true` recalls what their learning agents hold for that goal (a billed resolve per agent, at most six). They need the account's workflows feature, plus `agents:read`, `agents:write` (draft, save) or `agents:execute` (run). Runs and drafts are held against the account's spend limit.

### 2. Configure access

You need a **Hyperstruck API key** and (for learnings) usually an **agent id** that scopes stored knowledge.

**API key** (first match wins):

1. A key you paste in chat (never echoed back by the skill).
2. Environment variable **`HYPER_API_KEY`**.
3. A **`.env`** file in the project root, or a path pointed to by **`PUBLIC_INTEGRATIONS_ENV_FILE`**.
4. **`~/.hyperstruck/.env`** written by the IDE installer (desktop hosts only).

**Claude CoWork auth:** the remote session environment is often empty. That is not a missing key. The skill must also read `HYPER_*` from the **local filesystem** you attached — typically `.env` in that folder (then parent folders). Desktop CoWork can additionally read `~/.hyperstruck/.env` when that home directory is visible. Browser or cloud CoWork still cannot see a Mac home it was not granted; put a `.env` in the attached folder or grant that folder. Also set **`HYPER_SOURCE_FRAMEWORK=cowork`** so usage is attributed to CoWork instead of a Claude-skill default.

Skills and the IDE hook parse dotenv values like common dotenv loaders: strip one matching pair of surrounding quotes (`KEY="value"` / `KEY='value'`) and drop a trailing ` # comment` outside quotes, so secrets still produce a valid `Authorization: Bearer <key>` header. Prefer unquoted values in new files.

Send it on every request as:

`Authorization: Bearer <your key>`

**API base URL** — default **https://api.hyperstruck.com**. Override via conversation, **`HYPER_BASE_URL`**, or `.env`.

**Agent identity** — two env vars, two APIs:

| Variable | Used by | Value |
| -------- | ------- | ----- |
| **`HYPER_AGENT_NAME`** | Learning boundary (`POST /resolve`, `/observe`, `/reinforce`) and IDE hooks | Human-readable agent **name** (e.g. `support-bot`). If the name does not exist yet, the boundary **creates a learning agent with that name** on first use. |
| **`HYPER_AGENT_ID`** | REST skills (`GET/POST /agents/{agent_id}/...`) | Hosted agent **UUID** from `GET /agents` |
| **`HYPER_SPACE_ID`** | Agent listing (`GET /agents`) | Optional home-space **UUID**. When set, skills and install add `space_id` so a tenant with more than 50 agents still finds the match. |

Do **not** paste a Postgres UUID into `HYPER_AGENT_NAME` — the boundary would create a separate stub agent *named* with that UUID and learnings would land in the wrong corpus.

For **`hyper-learning`** REST calls:

1. You specify the UUID explicitly, or
2. **`HYPER_AGENT_ID`** / `.env`, or
3. The skill lists available agents (`GET /agents?limit=50`, plus `&space_id=$HYPER_SPACE_ID` when that var is set) and asks you to pick.

For the **IDE learning hook loop** (after `python -m hyperstruck.ide.install`), set **`HYPER_AGENT_NAME`**. The installer writes both vars automatically when you have a single agent.

### 3. Invoke from your assistant

Examples (exact slash syntax depends on your host):

```
/hyper-learning search retry backoff
/hyper-learning store
/hyper-learning reinforce <learning-id>
```

**`hyper-learning`** pre-approves the same HTTP tools so searches and writes do not trigger a permission prompt on every call.

On **Claude CoWork**, the skill *is* the learning loop. At the start of substantive work it calls `POST /resolve`, and it must close that run with `POST /reinforce` or `POST /decline` using the same `run_id`. It reads `HYPER_*` from the attached local `.env` as well as the remote session. Omit `resolve_purpose` so the platform defaults to `agent_loop` (that is what counts toward reporting). Use `explicit_recall` only when a human is inspecting recall and the run must not count. Do not use the IDE hook `--readonly` flag as the CoWork path.

Both skills can inject **current environment hints** at load time (for example whether `HYPER_API_KEY` is set) where the host supports inline shell in the skill body.

---

## Learn more

- **Product and platform:** [hyperstruck.com](https://hyperstruck.com)
- **Skill index:** [claude_skills/README.md](claude_skills/README.md)
- **Claude CoWork install:** [Getting started → Claude CoWork](#claude-cowork)

If you are extending or publishing this material from Hyperstruck’s private engineering repository, see the internal maintainer note in the platform repo: `docs/public-integrations-maintainers.md`.

Changes merged to `main` under `public_integrations/` are mirrored automatically to [hyperstruck/public-integrations](https://github.com/hyperstruck/public-integrations) by the `sync-public-integrations` GitHub Action. It runs on any commit reaching `main` that touches this directory, whatever put it there, so a change confined to files outside `public_integrations/` mirrors nothing and is expected to run no sync at all.

**The mirror runs one way.** Edit these files in the platform repository, never on the public one. A change merged directly on the public repository leaves its commit on a branch the mirror cannot reach: the next sync is *rejected* rather than overwriting it, so it fails silently on every subsequent merge and the two trees drift apart until someone reconciles them by hand. If a fix has already landed on the public side, bring it back first rather than pushing over it.
