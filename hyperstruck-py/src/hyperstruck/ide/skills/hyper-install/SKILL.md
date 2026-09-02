---
name: hyper-install
description: >-
  Install Hyperstruck learning into Claude Code and Cursor once per machine: it
  installs the hyper-* skills and wires the learning hooks so recall and capture
  happen automatically, with no manual skill calls during normal coding.
argument-hint: "[--agent-id <id>] [--space-id <uuid>]"
allowed-tools:
  - Bash(pip *)
  - Bash(pip3 *)
  - Bash(python3 *)
  - Bash(python *)
  - Bash(~/.hyperstruck/bootstrap/bin/python *)
---

# Install Hyperstruck IDE learning

Run this once per machine. It makes Hyperstruck learning automatic in your editor:
every coding turn recalls relevant prior learnings before the assistant acts and
contributes new learnings after, with no explicit skill calls in the common case.

## Steps

1. **Install the package** into a small bootstrap venv (it carries the skills,
   the hooks, and the loop; it is distributed from the public-integrations
   repository, not PyPI). A venv is needed because Homebrew's Python, and other
   externally managed Pythons, refuse a bare `pip install`:

```!
python3 -m venv --clear ~/.hyperstruck/bootstrap && ~/.hyperstruck/bootstrap/bin/python -m pip install --upgrade "hyperstruck @ git+https://github.com/hyperstruck/public-integrations.git#subdirectory=hyperstruck-py"
```

   If you already manage Python yourself (an activated venv, pyenv, conda), a
   plain `pip install --upgrade "hyperstruck @ ..."` there works too; run step 2
   with that same `python`.

2. **Wire it up.** Run the installer as a module with the interpreter from step 1
   so it uses the `hyperstruck` you just installed:

```!
~/.hyperstruck/bootstrap/bin/python -m hyperstruck.ide.install $ARGUMENTS
```

   This creates a durable venv at `~/.hyperstruck/venv`, installs/upgrades the
   running `hyperstruck` package into it, copies the `hyper-*` skills into
   `~/.claude/skills` and `~/.cursor/skills`, deep-merges the learning hooks into
   each editor's hooks config without touching your existing hooks, and records
   auth. Hook commands always call `$HOME/.hyperstruck/venv/bin/python` (or the
   Windows equivalent), **not** a project `.venv` interpreter — so a later
   `uv sync` / project venv recreate will not silently break hooks. On Homebrew
   the durable venv is built from `<prefix>/opt/python@3.x`, so it keeps working
   across Python patch upgrades.

   It detects which editors are present and only wires those. It is idempotent:
   re-running upgrades the durable venv and replaces Hyperstruck hook entries in
   place rather than duplicating. A durable venv whose interpreter no longer
   starts is rebuilt from scratch.

3. **Auth.** The wiring records `HYPER_API_KEY` (and optional `HYPER_BASE_URL`)
   into `~/.hyperstruck/.env`. If you have not exported a key, set one first and
   re-run step 2, or pass it explicitly:

```
~/.hyperstruck/bootstrap/bin/python -m hyperstruck.ide.install --api-key <key>
```

4. **Pick the agent the ambient loop feeds.** If you have a single Hyperstruck
   agent, the installer wires it automatically. If you have several, pass the one
   the ambient loop should use:

```
~/.hyperstruck/bootstrap/bin/python -m hyperstruck.ide.install --agent-id <agent-id>
```

   If the tenant has more than 50 agents, also pin the home space so listing does
   not miss the match. The installer writes `HYPER_SPACE_ID` into
   `~/.hyperstruck/.env`, and skills then pass it as `space_id` on `GET /agents`:

```
~/.hyperstruck/bootstrap/bin/python -m hyperstruck.ide.install --agent-name <name> --space-id <space-uuid>
```

   The explicit reasoning skills still select an agent per task; only the silent
   per-turn loop needs this default.

## After installing

- **Restart your editor** so it loads the new hooks and skills.
- Read the install report it prints: it lists what was installed, what was
  merged, and how to uninstall.
- The loop fails open everywhere: a missing key, a network error, or a malformed
  config degrades to a silent no-op and never blocks your editing.
- Re-run steps 1 and 2 after upgrading `hyperstruck` to refresh the durable
  venv and hook wiring.

## Troubleshooting

- **Every hook fails with `dyld: Library not loaded`** (macOS, usually after
  `brew upgrade` removed the Python release the durable venv was built from):
  re-run steps 1 and 2. The installer sees that `~/.hyperstruck/venv/bin/python`
  no longer starts and rebuilds the venv.

## Uninstall

```
~/.hyperstruck/bootstrap/bin/python -m hyperstruck.ide.install --uninstall
```

Removes only Hyperstruck's hook entries and skills; your other hooks are left
untouched. The durable `~/.hyperstruck/venv` is left in place so a re-install is
fast.
