# Hyperstruck Claude skills

These skills use the **`hyper-` prefix** on folder names and `name:` frontmatter so they are unlikely to collide with skills from other vendors or community packs when installed alongside them in `.claude/skills/`, `.cursor/skills/`, or Claude CoWork.

## Skills

| Folder / skill name | Purpose |
|---------------------|---------|
| `hyper-reasoning` | Invoke **Hyperstruck Core hosted reasoning** for stronger plans and analysis; wait for results and handle human-in-the-loop when required. |
| `hyper-learning` | **Search, store, retrieve, and reinforce learnings** so knowledge accumulates and future reasoning improves. |
| `hyper-plans` | **Search similar plans and review candidate learnings** for reuse and investigation. |

Each skill directory contains `SKILL.md` (main instructions). `hyper-plans` and `hyper-reasoning` also ship a `reference.md` with API shapes and error codes; `hyper-learning` instead resolves contract questions against the published [`openapi.json`](https://github.com/hyperstruck/public-integrations/blob/main/openapi.json) so it never goes stale.

## Installation options

**Manual copy (Claude Code / Cursor):** follow the copy or symlink steps in the [repository README](../README.md#getting-started).

**IDE installer (Claude Code / Cursor):** install [`hyperstruck-py`](../hyperstruck-py/) and run `python -m hyperstruck.ide.install`. That command deep-merges learning hooks into Claude Code and Cursor and installs the bundled skill copies from `hyperstruck-py/src/hyperstruck/ide/skills/` without overwriting your existing hook entries. It does **not** install or wire Claude CoWork.

**Claude CoWork:** zip `hyper-learning/` so the archive contains `hyper-learning/SKILL.md`, then in CoWork open **Customize → Skills** (or **+ → Skills → Add**) and **Upload a skill**. Enable it and start a new session. Allowlist `api.hyperstruck.com` for code-execution egress. CoWork has no hook loop — the skill calls `POST /resolve` and must close with `POST /reinforce` or `POST /decline`. It reads `HYPER_*` from the attached local `.env`, not only the remote session env. Set `HYPER_SOURCE_FRAMEWORK=cowork`. Full steps, auth, and reporting notes are in the [repository README](../README.md#claude-cowork).

For environment variables and how these skills fit together, see the [repository README](../README.md).
