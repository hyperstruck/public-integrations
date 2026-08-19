# Hyperstruck Claude skills

These skills use the **`hyper-` prefix** on folder names and `name:` frontmatter so they are unlikely to collide with skills from other vendors or community packs when installed alongside them in `.claude/skills/` or `.cursor/skills/`.

## Skills

| Folder / skill name | Purpose |
|---------------------|---------|
| `hyper-reasoning` | Invoke **Hyperstruck Core hosted reasoning** for stronger plans and analysis; wait for results and handle human-in-the-loop when required. |
| `hyper-learning` | **Search, store, retrieve, and reinforce learnings** so knowledge accumulates and future reasoning improves. |
| `hyper-plans` | **Search similar plans and review candidate learnings** for reuse and investigation. |

Each skill directory contains `SKILL.md` (main instructions). `hyper-plans` and `hyper-reasoning` also ship a `reference.md` with API shapes and error codes; `hyper-learning` instead resolves contract questions against the published [`openapi.json`](https://github.com/hyperstruck/public-integrations/blob/main/openapi.json) so it never goes stale.

## Installation options

**Manual copy:** follow the copy or symlink steps in the [repository README](../README.md#getting-started).

**IDE installer:** install [`hyperstruck-py`](../hyperstruck-py/) and run `python -m hyperstruck.ide.install`. That command deep-merges learning hooks into Claude Code and Cursor and installs the bundled skill copies from `hyperstruck-py/src/hyperstruck/ide/skills/` without overwriting your existing hook entries.

For environment variables and how these skills fit together, see the [repository README](../README.md).
