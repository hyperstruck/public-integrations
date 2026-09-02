"""What a host's tools are, judged once out of band and read back by name.

Classification used to happen inside the tool hook, by matching substrings of the tool's
name. That decided what the corpus could ever contain: a tool from any MCP server matched
nothing, fell to ``other``, and ``other`` is not material, so browser automation, API
calls, messaging and most non-coding agent work never cleared the observe gate and were
never learned from at all.

The judgement cannot move into the hook. A tool event carries a name, its inputs, its
response and an id, and nothing else: no description, no MCP annotations, no category. And
every hook event is a fresh short-lived subprocess, so there is no warm cache and "judge
once" cannot mean "once per process". So the verdict is written here, out of band, and the
hook does a dictionary lookup.

Nothing here infers. A verdict comes from a closed, published, host-declared vocabulary
that already means what is needed: MCP's ``readOnlyHint`` annotation and the platform's own
``ToolSpec.category``. Mapping one closed enum onto another is translation.

Only ``readOnlyHint`` is read, because read-only is the only verdict that takes a tool *out*
of the material set and everything else is an act. ``destructiveHint`` would refine which
kind of act, which nothing here branches on; the declared category is carried through
verbatim for the server, which does.

Two things are recorded rather than one. Registration knows which servers the host
*declared* as well as which ones actually answered, because "registration succeeded" and
"this is the whole tool set" are different claims when MCP servers connect dynamically,
and only the second licenses sending a tool palette.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from hyperstruck._wire import ToolSpec
from hyperstruck.ide.constants import (
    MAX_MODEL_CONTEXT_WINDOW,
    MAX_PALETTE_TOOLS,
    MAX_REGISTERED_TOOL_NAME_CHARS,
    MIN_MODEL_CONTEXT_WINDOW,
    REGISTRATION_SUBDIR,
    REGISTRATION_TTL_SECONDS,
    STEP_KIND_ACT,
    STEP_KIND_READ,
    hyper_home,
)
from hyperstruck.ide.state import read_json, safe_name, write_json_atomic
from hyperstruck.redaction import scrub_secrets

# The platform's own tool categories. ``read_only`` is the only one that is not an act, so
# it is the only one that can take a tool out of the material set. The others are kept
# verbatim rather than re-derived: the server reads a tool's category to tell a write from
# a delegation from an external call, and collapsing them all to one value would tell it
# every tool this host has is the same kind of thing.
_READ_ONLY_CATEGORY = "read_only"
_DEFAULT_ACT_CATEGORY = "external"
_KNOWN_CATEGORIES = frozenset(
    {_READ_ONLY_CATEGORY, "write", "destructive", "external", "delegation"}
)


def registration_path(source: str) -> Path:
    return hyper_home() / REGISTRATION_SUBDIR / f"{safe_name(source)}.json"


def register(
    source: str,
    tools: list[dict[str, Any]],
    *,
    declared_servers: list[str] | None = None,
    registered_servers: list[str] | None = None,
    model_context_window: int | None = None,
) -> None:
    """Record what this host's tools are, and how much of its tool set this covers."""
    write_json_atomic(
        registration_path(source),
        {
            "source": source,
            "written_at": time.time(),
            "declared_servers": sorted(set(declared_servers or ())),
            "registered_servers": sorted(set(registered_servers or ())),
            "model_context_window": _bounded_window(model_context_window),
            "declared_tool_count": len([t for t in tools if t.get("name")]),
            "tools": _bounded_tools(tools),
        },
    )


def _bounded_tools(tools: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """What a registration may record, bounded because its payload is not trusted.

    The ``register`` command reads a local payload, and this client's own comments already
    note that its CLI is invocable by any agent with a shell. An unbounded list would ride
    every subsequent resolve and cost the turn its recall when the boundary refused it, so
    the surplus is dropped here where the loss is one tool rather than the whole request.
    """
    recorded: dict[str, dict[str, str]] = {}
    for tool in tools:
        name = str(tool.get("name") or "")[:MAX_REGISTERED_TOOL_NAME_CHARS].strip()
        if not name or name in recorded:
            continue
        if len(recorded) >= MAX_PALETTE_TOOLS:
            break
        kind = _kind_of(tool)
        recorded[scrub_secrets(name)] = {
            "kind": kind,
            "category": _category_of(tool, kind),
        }
    return recorded


def _bounded_window(window: Any) -> int | None:
    """A declared context window, or nothing when what was declared is not one."""
    if isinstance(window, bool) or not isinstance(window, int):
        return None
    return (
        window
        if MIN_MODEL_CONTEXT_WINDOW <= window <= MAX_MODEL_CONTEXT_WINDOW
        else None
    )


def registered_kind(source: str, tool_name: str) -> str | None:
    """The stored verdict for one tool, or nothing when there is none to read.

    A pure lookup. It performs no work a miss could trigger, because it is called from
    inside the tool hook, on the editor's path, once per tool call.
    """
    entry = (_live_record(source) or {}).get("tools", {}).get(tool_name)
    return str(entry["kind"]) if isinstance(entry, dict) and entry.get("kind") else None


def palette(
    source: str, record: dict[str, Any] | None = None
) -> tuple[ToolSpec, ...] | None:
    """This host's tools, but only when the registration covers all of them.

    A null palette fails open, and a *partial* one suppresses real rules: the server
    reads the absence of a tool as the agent not having it. So a registration that
    reached three of five declared servers keeps its classifications, which are useful
    per tool, and sends nothing, which is today's behaviour. Anything else would suppress
    exactly the MCP-targeted rules the classification above exists to start earning, and
    it would surface as unexplained missing advice rather than as an error.
    """
    record = _live_record(source) if record is None else record
    if record is None:
        return None
    if set(record.get("declared_servers") or ()) - set(
        record.get("registered_servers") or ()
    ):
        return None
    tools = record.get("tools") or {}
    # Against the count BEFORE the cap. Checking the stored count could never fire, because
    # storing already truncates to the cap: the guard existed and was unreachable, so a host
    # with more tools than the cap shipped exactly the silently-partial palette this refuses.
    if record.get("declared_tool_count", len(tools)) > MAX_PALETTE_TOOLS:
        return None
    if not tools:
        return None
    return tuple(
        ToolSpec(name=name, category=entry.get("category") or _DEFAULT_ACT_CATEGORY)
        for name, entry in tools.items()
        if isinstance(entry, dict)
    )


def live_record(source: str) -> dict[str, Any] | None:
    """One read of this host's registration, for a caller that needs more than one answer.

    ``_aresolve`` wants the palette and the window together, and each was opening and
    parsing the whole file for itself, on the recall path.
    """
    return _live_record(source)


def context_window(source: str, record: dict[str, Any] | None = None) -> int | None:
    """The window this host declared, or nothing when it declared none.

    Shipped whatever the palette does: it is a budget hint, so it can only change how
    much is sent back, never which rules are eligible, and a partial one suppresses
    nothing.
    """
    record = _live_record(source) if record is None else record
    if record is None:
        return None
    return _bounded_window(record.get("model_context_window"))


def _live_record(source: str) -> dict[str, Any] | None:
    record = read_json(registration_path(source))
    if not isinstance(record, dict):
        return None
    try:
        age = time.time() - float(record.get("written_at") or 0.0)
    except (TypeError, ValueError):
        return None
    return record if 0 <= age <= REGISTRATION_TTL_SECONDS else None


def _kind_of(tool: dict[str, Any]) -> str:
    """One tool's step kind, translated from whichever vocabulary declared it.

    Read-only is the only verdict that takes a tool *out* of the material set, so it is
    the only one this asks about. Everything else acts, and ``act`` is deliberately not
    ``command``: the execution oracle reads the trailing command step as the turn's
    verdict, and an unrelated API call is not a verdict on anything.
    """
    annotations = tool.get("annotations")
    if isinstance(annotations, dict) and annotations.get("readOnlyHint") is True:
        return STEP_KIND_READ
    if tool.get("category") == _READ_ONLY_CATEGORY:
        return STEP_KIND_READ
    return STEP_KIND_ACT


def _category_of(tool: dict[str, Any], kind: str) -> str:
    """The category to report to the server: the declared one wherever there is one.

    Re-deriving it from the step kind would report every non-read-only tool as ``external``,
    losing the write / destructive / delegation distinctions the server reads to tell a run
    that held off from an act apart from one that had nothing to hold off from.
    """
    declared = tool.get("category")
    if declared in _KNOWN_CATEGORIES:
        return str(declared)
    return _READ_ONLY_CATEGORY if kind == STEP_KIND_READ else _DEFAULT_ACT_CATEGORY
