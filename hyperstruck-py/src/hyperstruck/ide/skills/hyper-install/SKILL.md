---
name: hyper-install
description: >-
  Install Hyperstruck learning into Claude Code and Cursor once per machine: it
  installs the hyper-* skills and wires the learning hooks so recall and capture
  happen automatically, with no manual skill calls during normal coding.
argument-hint: "[--agent-id <id>]"
allowed-tools:
  - Bash(pip *)
  - Bash(pip3 *)
  - Bash(python3 *)
  - Bash(python *)
---

# Install Hyperstruck IDE learning

Run this once per machine. It makes Hyperstruck learning automatic in your editor:
every coding turn recalls relevant prior learnings before the assistant acts and
contributes new learnings after, with no explicit skill calls in the common case.

## Steps

1. **Install the package** (it carries the skills, the hooks, and the loop):

```!
pip install --upgrade hyperstruck
```

2. **Wire it up.** This copies the `hyper-*` skills into `~/.claude/skills` and
   `~/.cursor/skills`, deep-merges the learning hooks into each editor's hooks
   config without touching your existing hooks, writes the Cursor recall nudge,
   and records auth. It detects which editors are present and only wires those. It
   is idempotent: re-running upgrades in place rather than duplicating.

```!
python3 -m hyperstruck.ide.install $ARGUMENTS
```

3. **Auth.** The wiring records `HYPER_API_KEY` (and optional `HYPER_BASE_URL`)
   into `~/.hyperstruck/.env`. If you have not exported a key, set one first and
   re-run step 2, or pass it explicitly:

```
python3 -m hyperstruck.ide.install --api-key <key>
```

4. **Pick the agent the ambient loop feeds.** If you have a single Hyperstruck
   agent, the installer wires it automatically. If you have several, pass the one
   the ambient loop should use:

```
python3 -m hyperstruck.ide.install --agent-id <agent-id>
```

   The explicit reasoning skills still select an agent per task; only the silent
   per-turn loop needs this default.

## After installing

- **Restart your editor** so it loads the new hooks and skills.
- Read the install report it prints: it lists what was installed, what was
  merged, and how to uninstall.
- The loop fails open everywhere: a missing key, a network error, or a malformed
  config degrades to a silent no-op and never blocks your editing.

## Uninstall

```
python3 -m hyperstruck.ide.install --uninstall
```

Removes only Hyperstruck's hook entries, skills, and the Cursor nudge; your other
hooks are left untouched.
