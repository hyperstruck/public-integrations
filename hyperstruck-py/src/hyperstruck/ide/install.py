"""Install the IDE learning loop into Claude Code and/or Cursor.

Idempotent and additive. It copies the bundled ``hyper-*`` skills into each
editor's user-global skill directory, deep-merges the learning hooks into the
editor's hooks config *without* touching any other entry, and records auth.
Re-running upgrades in place: our entries carry a
recognisable command marker, so a re-run replaces them rather than duplicating,
and never removes a hook another tool installed.

Hook commands always run under a durable venv at ``~/.hyperstruck/venv`` (not
the project interpreter). Project ``uv sync`` / venv recreates drop undeclared
packages and would silently break hooks if they pointed at ``sys.executable``.

Every editor is handled independently and best-effort: a missing editor is
skipped, and a present-but-unparseable config is backed up and left untouched
rather than overwritten. The loop is strictly opt-in per machine and per editor.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import venv
from dataclasses import dataclass, field
from importlib import metadata, resources
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from hyperstruck.ide.config import load_env
from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    env_file,
    ide_venv_dir,
)

# The command marker: any hook entry whose command contains this is ours, so a
# re-run replaces it (upgrade) and an uninstall removes exactly our entries.
_MARKER = "hyperstruck.ide.hook"


def _claude_dir() -> Path:
    """Claude Code's user dir, overridable for tests and exotic homes."""
    return Path(os.environ.get("HYPER_CLAUDE_DIR") or (Path.home() / ".claude"))


def _cursor_dir() -> Path:
    """Cursor's user dir, overridable for tests and exotic homes."""
    return Path(os.environ.get("HYPER_CURSOR_DIR") or (Path.home() / ".cursor"))


@dataclass
class Report:
    """A human-readable record of what the install did, per editor."""

    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def did(self, message: str) -> None:
        self.actions.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def render(self) -> str:
        lines = ["Hyperstruck IDE learning install:"]
        lines += [f"  [ok] {a}" for a in self.actions] or ["  (nothing to do)"]
        if self.warnings:
            lines += [f"  [!] {w}" for w in self.warnings]
        lines.append(
            "\nTo uninstall: run `python -m hyperstruck.ide.install --uninstall` "
            "(removes only Hyperstruck hook entries and skills)."
        )
        return "\n".join(lines)


# -- public API --------------------------------------------------------------


def install(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    agent_id: str | None = None,
    validate: bool = True,
) -> Report:
    """Install skills, wire hooks, and record auth for every editor present."""
    report = Report()
    durable_ready = _ensure_durable_venv(report)
    key, url = _write_auth(report, api_key=api_key, base_url=base_url)
    _resolve_ambient_agent(report, agent_id=agent_id, key=key, base_url=url)

    if _claude_dir().is_dir():
        _install_claude(report, wire_hooks=durable_ready)
    else:
        report.did("Claude Code not found (~/.claude absent); skipped")
    if _cursor_dir().is_dir():
        _install_cursor(report, wire_hooks=durable_ready)
    else:
        report.did("Cursor not found (~/.cursor absent); skipped")

    if validate:
        _validate_auth(report)
    return report


def uninstall() -> Report:
    """Remove only Hyperstruck hook entries and skills.

    Leaves the durable IDE venv in place so a re-install is fast; hooks and
    skills are what opt the machine into the loop.
    """
    report = Report()
    _unwire(report, _claude_dir() / "settings.json", _claude_events())
    _unwire(report, _cursor_dir() / "hooks.json", _cursor_events())
    for editor_dir in (_claude_dir(), _cursor_dir()):
        for skill in _bundled_skill_names():
            target = editor_dir / "skills" / skill
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                report.did(f"Removed skill {target}")
    # Legacy cleanup: earlier versions wrote a Cursor recall rule, now superseded
    # by the beforeSubmitPrompt/postToolUse hooks. Remove it if a prior install left it.
    rule = _cursor_dir() / "rules" / "hyperstruck-learning.mdc"
    if rule.exists():
        rule.unlink()
        report.did(f"Removed legacy {rule}")
    return report


# -- Claude Code -------------------------------------------------------------


def _install_claude(report: Report, *, wire_hooks: bool = True) -> None:
    _copy_skills(_claude_dir() / "skills", report)
    if not wire_hooks:
        report.warn(
            "Skipping Claude Code hook rewire; durable venv is not importable "
            "(existing hook wiring left in place)"
        )
        return
    settings_path = _claude_dir() / "settings.json"
    config = _load_json_config(settings_path, report)
    if config is None:
        return
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        report.warn(f"{settings_path}: 'hooks' is not an object; left untouched")
        return
    for event, command in _claude_events().items():
        groups = [
            g
            for g in hooks.get(event, [])
            if isinstance(g, dict) and not _group_is_ours(g)
        ]
        group: dict[str, Any] = {"hooks": [{"type": "command", "command": command}]}
        if event == "PostToolUse":
            group["matcher"] = "*"
        groups.append(group)
        hooks[event] = groups
    _write_json_atomic(settings_path, config)
    report.did(f"Wired Claude Code hooks in {settings_path}")


# -- Cursor ------------------------------------------------------------------


def _install_cursor(report: Report, *, wire_hooks: bool = True) -> None:
    _copy_skills(_cursor_dir() / "skills", report)
    if not wire_hooks:
        report.warn(
            "Skipping Cursor hook rewire; durable venv is not importable "
            "(existing hook wiring left in place)"
        )
        return
    hooks_path = _cursor_dir() / "hooks.json"
    config = _load_json_config(hooks_path, report)
    if config is None:
        return
    config.setdefault("version", 1)
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        report.warn(f"{hooks_path}: 'hooks' is not an object; left untouched")
        return
    for event, command in _cursor_events().items():
        entries = [
            e
            for e in hooks.get(event, [])
            if isinstance(e, dict) and _MARKER not in str(e.get("command", ""))
        ]
        entries.append({"command": command})
        hooks[event] = entries
    _write_json_atomic(hooks_path, config)
    report.did(f"Wired Cursor hooks in {hooks_path}")


# -- durable IDE venv --------------------------------------------------------


def _venv_python(venv_dir: Path) -> Path:
    """Interpreter path inside a venv (POSIX ``bin/`` vs Windows ``Scripts/``)."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _hook_python() -> str:
    """Python used in wired hook commands: durable venv, never ``sys.executable``."""
    return str(_venv_python(ide_venv_dir()))


def _ensure_durable_venv(report: Report) -> bool:
    """Create ``~/.hyperstruck/venv`` if needed and sync the running package into it.

    Returns True only when the durable interpreter can ``import hyperstruck``.
    Callers must not rewire hooks to the durable path when this returns False,
    so a failed create/install leaves any existing (working) wiring in place.
    """
    venv_dir = ide_venv_dir()
    python = _venv_python(venv_dir)
    if not python.is_file():
        try:
            venv_dir.parent.mkdir(parents=True, exist_ok=True)
            venv.create(str(venv_dir), with_pip=True, clear=False)
            report.did(f"Created durable IDE venv at {venv_dir}")
        except Exception as exc:  # noqa: BLE001 - best-effort; warn and continue
            report.warn(f"Could not create durable IDE venv at {venv_dir}: {exc}")
            return False
    _sync_package_into_venv(report, venv_dir)
    if not _durable_venv_importable(report, venv_dir):
        return False
    return True


def _durable_venv_importable(report: Report, venv_dir: Path) -> bool:
    """True when the durable venv can import hyperstruck (safe to rewire hooks)."""
    python = _venv_python(venv_dir)
    if not python.is_file():
        report.warn(
            f"Durable IDE venv python missing at {python}; "
            "leaving existing hook wiring in place"
        )
        return False
    try:
        result = subprocess.run(
            [str(python), "-c", "import hyperstruck"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report.warn(
            f"Could not verify durable IDE venv import: {exc}; "
            "leaving existing hook wiring in place"
        )
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        report.warn(
            f"Durable IDE venv cannot import hyperstruck{suffix}; "
            "leaving existing hook wiring in place"
        )
        return False
    return True


def _sync_package_into_venv(report: Report, venv_dir: Path) -> None:
    """Install/upgrade the running hyperstruck distribution into the durable venv."""
    python = _venv_python(venv_dir)
    if not python.is_file():
        report.warn(
            f"Durable IDE venv python missing at {python}; hooks may fail until install succeeds"
        )
        return
    target = _running_package_pip_target()
    if target is None:
        report.warn(
            "Could not locate the running hyperstruck package to install into the durable venv"
        )
        return
    try:
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", target],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report.warn(f"Failed to install hyperstruck into durable venv: {exc}")
        return
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        report.warn(f"Failed to install hyperstruck into durable venv{suffix}")
        return
    report.did(f"Installed hyperstruck into durable venv ({venv_dir})")


def _running_package_pip_target() -> str | None:
    """Pip install target matching the hyperstruck package that is running this installer.

    Prefers a local path (checkout / editable install) so the durable venv gets the
    same code that invoked install; falls back to a version pin when only a wheel
    distribution is available.
    """
    local = _local_package_root()
    if local is not None:
        return str(local)

    try:
        dist = metadata.distribution("hyperstruck")
    except metadata.PackageNotFoundError:
        return None

    direct_path = _direct_url_path(dist)
    if direct_path is not None:
        return str(direct_path)

    version = dist.version
    if version:
        return f"hyperstruck=={version}"
    return "hyperstruck"


def _local_package_root() -> Path | None:
    """Package root when running from a source tree (``pyproject.toml`` nearby)."""
    here = Path(__file__).resolve()
    # install.py -> ide -> hyperstruck -> src -> <package root>
    candidates = []
    if len(here.parents) > 3:
        candidates.append(here.parents[3])
    if len(here.parents) > 2:
        candidates.append(here.parents[2])
    for parent in candidates:
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            continue
        if 'name = "hyperstruck"' in text or "name = 'hyperstruck'" in text:
            return parent
    return None


def _direct_url_path(dist: metadata.Distribution) -> Path | None:
    """File path from an editable / direct_url install, if present."""
    try:
        raw = dist.read_text("direct_url.json")
    except (OSError, FileNotFoundError, UnicodeDecodeError):
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        url = data.get("url") or ""
    except (ValueError, AttributeError, TypeError):
        return None
    if not url.startswith("file:"):
        return None
    parsed = urlparse(url)
    path = unquote(parsed.path)
    # Windows file URLs are often ``file:///C:/...`` → path ``/C:/...``.
    if os.name == "nt" and len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    candidate = Path(path)
    try:
        if candidate.exists():
            return candidate
    except OSError:
        return None
    return None


# -- hook command definitions ------------------------------------------------


def _hook_cmd(command: str, *extra: str) -> str:
    parts = [shlex.quote(_hook_python()), "-m", "hyperstruck.ide.hook", command, *extra]
    return " ".join(parts)


def _claude_events() -> dict[str, str]:
    return {
        "UserPromptSubmit": _hook_cmd("prompt", "--source", SOURCE_CLAUDE_CODE),
        "PostToolUse": _hook_cmd("tool", "--source", SOURCE_CLAUDE_CODE),
        "Stop": _hook_cmd("stop", "--source", SOURCE_CLAUDE_CODE),
    }


def _cursor_events() -> dict[str, str]:
    # Cursor's prompt hook cannot inject, so resolve runs on beforeSubmitPrompt
    # (stashes the recall, keyed by conversation_id) and the recall is injected by
    # postToolUse, the one tool event that can return additional_context. Capture
    # rides on afterFileEdit/afterShellExecution (the file/shell events) so it
    # never double-counts a tool the inject hook also sees. All five hooks receive
    # conversation_id, so resolve and capture rendezvous on the same session.
    return {
        "beforeSubmitPrompt": _hook_cmd("prompt", "--source", SOURCE_CURSOR),
        "postToolUse": _hook_cmd("tool", "--source", SOURCE_CURSOR, "--inject"),
        "afterFileEdit": _hook_cmd("tool", "--source", SOURCE_CURSOR, "--kind", "edit"),
        "afterShellExecution": _hook_cmd(
            "tool", "--source", SOURCE_CURSOR, "--kind", "command"
        ),
        "stop": _hook_cmd("stop", "--source", SOURCE_CURSOR),
    }


def _group_is_ours(group: dict[str, Any]) -> bool:
    """Whether a Claude hook group contains one of our command entries."""
    for entry in group.get("hooks", []) or []:
        if isinstance(entry, dict) and _MARKER in str(entry.get("command", "")):
            return True
    return False


# -- skills ------------------------------------------------------------------


def _copy_skills(target_dir: Path, report: Report) -> None:
    source = _skills_resource_dir()
    if source is None:
        report.warn("Bundled skills not found in the package; skipped skill copy")
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for skill in sorted(source.iterdir()):
        if not skill.is_dir():
            continue
        shutil.copytree(skill, target_dir / skill.name, dirs_exist_ok=True)
    report.did(f"Installed skills into {target_dir}")


def _bundled_skill_names() -> list[str]:
    source = _skills_resource_dir()
    if source is None:
        return []
    return [p.name for p in source.iterdir() if p.is_dir()]


def _skills_resource_dir() -> Path | None:
    try:
        path = resources.files("hyperstruck.ide").joinpath("skills")
    except (ModuleNotFoundError, AttributeError):
        return None
    real = Path(str(path))
    return real if real.is_dir() else None


# -- auth --------------------------------------------------------------------


def _write_auth(
    report: Report, *, api_key: str | None, base_url: str | None
) -> tuple[str | None, str | None]:
    key = (
        api_key
        or os.environ.get("HYPER_API_KEY")
        or os.environ.get("HYPERSTRUCK_API_KEY")
    )
    url = (
        base_url
        or os.environ.get("HYPER_BASE_URL")
        or os.environ.get("HYPERSTRUCK_BASE_URL")
    )
    if not key and not url:
        report.warn(
            "No API key provided; set HYPER_API_KEY (and optionally HYPER_BASE_URL) "
            f"in {env_file()} so the loop can authenticate"
        )
        return key, url
    _upsert_env({"HYPER_API_KEY": key, "HYPER_BASE_URL": url})
    report.did(f"Recorded auth in {env_file()} (gitignored; do not commit)")
    return key, url


def _resolve_ambient_agent(
    report: Report, *, agent_id: str | None, key: str | None, base_url: str | None
) -> None:
    """Pick the agent the ambient hook loop feeds, and persist it as HYPER_AGENT_ID.

    Identity is the customer's configured agent, never the repo. An explicit
    choice wins; otherwise a single-agent tenant is wired automatically; a
    multi-agent tenant is left for the user to choose (the skills still select an
    agent per task, so only the ambient loop waits on this).
    """
    chosen = (
        agent_id
        or os.environ.get("HYPER_AGENT_ID")
        or os.environ.get("HYPER_LEARNING_AGENT_ID")
    )
    if not chosen and key:
        agents = _list_agents(key, base_url)
        if len(agents) == 1:
            chosen = agents[0].get("id") or agents[0].get("agent_id")
        elif len(agents) > 1:
            report.warn(
                "You have multiple agents; the ambient loop needs one to feed. Re-run with "
                "--agent-id <id> (or set HYPER_AGENT_ID). The skills still pick an agent per task."
            )
        else:
            report.warn(
                "No agents found for this key; create one in the dashboard, then re-run."
            )
    if chosen:
        _upsert_env({"HYPER_AGENT_ID": chosen})
        report.did(f"Ambient loop will learn into agent {chosen}")


def _list_agents(key: str, base_url: str | None) -> list[dict[str, Any]]:
    """Best-effort list of the tenant's agents; empty on any error."""
    base = (base_url or "https://api.hyperstruck.com").rstrip("/")
    try:
        import httpx

        response = httpx.get(
            f"{base}/agents",
            params={"limit": 50},
            headers={"Authorization": f"Bearer {key}"},
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
    except (
        Exception
    ):  # noqa: BLE001 - listing is best-effort; warn paths handle empties
        return []
    items = data.get("items") if isinstance(data, dict) else data
    return [a for a in (items or []) if isinstance(a, dict)]


def _validate_auth(report: Report) -> None:
    load_env()  # fold ~/.hyperstruck/.env into the environment (no override)
    key = os.environ.get("HYPER_API_KEY")
    if not key:
        return  # already warned in _write_auth
    base = (os.environ.get("HYPER_BASE_URL") or "https://api.hyperstruck.com").rstrip(
        "/"
    )
    # Validate with a read-only GET /agents, never a resolve: resolve auto-upserts
    # the agent it is given, which would persist a phantom probe agent in the tenant.
    try:
        import httpx

        response = httpx.get(
            f"{base}/agents",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {key}"},
            timeout=5.0,
        )
    except Exception as exc:  # noqa: BLE001 - warn, never fail the install
        report.warn(
            f"Could not reach the boundary to validate auth ({type(exc).__name__}); the loop still installs and fails open"
        )
        return
    if response.status_code == 200:
        report.did("Validated auth against the boundary")
    elif response.status_code in (401, 403):
        report.warn("Auth check failed (401/403): verify HYPER_API_KEY")
    else:
        report.warn(
            f"Auth check returned HTTP {response.status_code}; the loop still installs and fails open"
        )


# -- config IO ---------------------------------------------------------------


def _load_json_config(path: Path, report: Report) -> dict[str, Any] | None:
    """Load an editor config, or back up and skip an unparseable one."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            shutil.copy2(path, backup)
        except OSError:
            pass
        report.warn(
            f"{path} is unparseable; backed up to {backup} and left it untouched"
        )
        return None
    if not isinstance(data, dict):
        report.warn(f"{path} is not a JSON object; left untouched")
        return None
    return data


def _unwire(report: Report, path: Path, events: dict[str, str]) -> None:
    if not path.is_file():
        return
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return
    changed = False
    for event in events:
        existing = hooks.get(event)
        if not isinstance(existing, list):
            continue
        kept = [e for e in existing if not _entry_is_ours(e)]
        if len(kept) != len(existing):
            hooks[event] = kept
            changed = True
    if changed:
        _write_json_atomic(path, config)
        report.did(f"Removed Hyperstruck hooks from {path}")


def _entry_is_ours(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if _MARKER in str(entry.get("command", "")):
        return True
    return _group_is_ours(entry)


def _upsert_env(updates: dict[str, str | None]) -> None:
    """Merge keys into ``~/.hyperstruck/.env`` without disturbing existing lines."""
    path = env_file()
    existing: dict[str, str] = {}
    order: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                existing[key] = line.split("=", 1)[1].strip()
                order.append(key)
    for key, value in updates.items():
        if value is None:
            continue
        if key not in existing:
            order.append(key)
        existing[key] = value
    body = "".join(f"{key}={existing[key]}\n" for key in dict.fromkeys(order))
    _write_text_atomic(path, body, mode=0o600)


def _write_json_atomic(path: Path, obj: Any) -> None:
    _write_text_atomic(path, json.dumps(obj, indent=2) + "\n")


def _write_text_atomic(path: Path, text: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    if mode is not None:
        # Create the temp file with the restrictive mode from the start (the .env
        # carries the API key), so there is no world-readable window before chmod.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, mode)  # O_CREAT mode is umask-masked; enforce it exactly
    else:
        tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# -- CLI ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hyperstruck.ide.install")
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove Hyperstruck hooks and skills"
    )
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument(
        "--agent-id",
        default=None,
        help="Agent the ambient loop feeds (defaults to your single agent)",
    )
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args(argv)
    report = (
        uninstall()
        if args.uninstall
        else install(
            api_key=args.api_key,
            base_url=args.base_url,
            agent_id=args.agent_id,
            validate=not args.no_validate,
        )
    )
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
