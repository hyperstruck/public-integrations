---
name: platform-cognitive-loop
description: >-
  End-to-end dogfooding loop for Claude Code: handoff, recall learnings, hosted agent goal
  with polling, then store new learnings. Combines platform-context-handoff, platform-learnings-recall,
  platform-agent-run, and platform-learnings.
---

# Cognitive loop: recall → remote reasoning → persist learnings

## Intent

Use the hosted platform to add **deeper reasoning** on top of local Claude Code work, then **capture learnings** so future runs start smarter.

## Ordered steps

1. **platform-context-handoff** — Build the full context bundle (goal, tools, prior chat insights, constraints).
2. **platform-learnings-recall** — Search (and optionally get) learnings relevant to the goal; merge into the `context` string for the next step.
3. **platform-agent-run** — **POST** `/agents/{agent_id}/goals` with rich `goal` + `context`. Poll **GET** `/runs/{run_id}` until `completed`, `failed`, or `suspended`.
4. If **suspended**, get human decision and **POST** `/runs/{run_id}/resume`; then poll the continuation run.
5. **platform-learnings** — Store 1–n concise learnings (`pitfall`, `approach`, `tool_usage`, etc.) derived from **this session** (local work + remote run summary). Wait briefly after **202** responses before verifying via search.
6. Optionally **reinforce** older learnings if this session confirmed or refuted them.

## Authentication

Resolve `HYPER_API_KEY` and never print it:

1. User message / secure env injection.
2. `HYPER_API_KEY`.
3. `.env` or `PUBLIC_INTEGRATIONS_ENV_FILE`.

Also require `HYPER_BASE_URL` and `HYPER_AGENT_ID`.

## Session continuity

- First iteration: omit `session_id` on the goal to create a session.
- Later iterations on the same project: reuse `session_id` only when no non-terminal run exists (**409** otherwise).

## What to tell the human at the end

- Remote run outcome and key takeaways.
- New `learning_id` values only if useful for bookmarks (they are not secrets).
- Suggested next search queries for the **next** cognitive loop.

## Alternatives

- Curl-only agent steps: **platform-agent-run-curl**.
- Learning-only capture without a remote run: **platform-learnings** alone.
