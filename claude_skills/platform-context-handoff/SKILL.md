---
name: platform-context-handoff
description: >-
  Before calling a hosted agent or learnings API, gather a structured handoff:
  goal summary, prior learnings from chat, tools used, constraints. Use with
  platform-agent-run and platform-learnings skills.
---

# Context handoff for platform agent + learnings calls

## When to use

Invoke this skill **before** dispatching a remote agent goal or writing learnings. The coding agent (Claude Code, Cursor, etc.) should not call the platform with a one-line prompt when the human has rich local context.

## Required context bundle (ask the human / scan the thread)

Collect and pass through explicitly:

1. **Goal summary** — One short paragraph: what “done” looks like and success criteria.
2. **Background** — Repo, environment, branch, and any non-obvious constraints (timeouts, regions, compliance).
3. **Prior learnings** — Bullet list of insights already discovered in this chat (pitfalls, approaches, prerequisites). Mark which are **new** vs **confirmed**.
4. **Tools and data** — Which tools or APIs were already invoked; paste **summaries** of outputs, not secrets (redact tokens, PII, internal hostnames if needed).
5. **Open questions** — What the hosted agent should **not** assume; what still needs verification.

## API key (do not echo)

Resolve credentials without printing the secret:

1. Explicit key or env block from the human (never log it).
2. Environment variable `HYPER_API_KEY`.
3. `.env` in the project root or path in `PUBLIC_INTEGRATIONS_ENV_FILE` (keys: `HYPER_API_KEY`, optionally `HYPER_BASE_URL`, `HYPER_AGENT_ID`).

If missing, stop and ask the human to set one of the above.

## Output format for downstream skills

Produce a single markdown block the next skill can consume:

```markdown
## Platform handoff
- Base URL: <HYPER_BASE_URL>
- Agent ID: <HYPER_AGENT_ID>
- Goal: ...
- Context for API: ...  # distilled from sections above
- Session policy: [new session | continue session SESSION_ID]
```

## Safety

- Do not paste API keys into tickets, commits, or public repos.
- This folder may be published; keep examples generic.
