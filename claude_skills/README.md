# Hyperstruck Claude skills

These skills use the **`hyper-` prefix** on folder names and `name:` frontmatter so they are unlikely to collide with skills from other vendors or community packs when installed alongside them in `.claude/skills/` or `.cursor/skills/`.

## Skills

| Folder / skill name | Purpose |
|---------------------|---------|
| `hyper-reasoning` | Invoke **Hyperstruck Core hosted reasoning** for stronger plans and analysis; wait for results and handle human-in-the-loop when required. |
| `hyper-learning` | **Search, store, retrieve, and reinforce learnings** so knowledge accumulates and future reasoning improves. |

Each skill directory contains `SKILL.md` (main instructions) and `reference.md` (API shapes and error codes).

For installation, environment variables, and how these fit together, see the [repository README](../README.md).
