"""Experience carried from this project's last turn, so the model has it before it acts.

A turn's own recall is resolved off the editor's critical path and lands after the prompt
hook has already returned, so it can only be shown on a tool event. The opening plan and
the first tool choice are therefore always made with nothing, which is where the choices
that matter are made.

What this holds is the previous resolve for the same project, ready at prompt time. It is
a speculative prefetch rather than an answer: it was bound against a different goal, and
this client cannot re-evaluate a binding locally. So it is never presented as established
for the turn reading it. Every emission declares where it came from and how old it is,
after ``stale-while-revalidate`` (RFC 5861) paired with HTTP's ``Age``: serve the stale
value immediately and tell the consumer exactly how stale, so it can discount the thing
itself rather than being misled by it.

Scope is the project, not the session. Rules are earned against a codebase's conventions,
so the project is where relevance actually breaks; per-session keying would miss the cold
start, which is the case with the most to gain. Crossing projects is the one boundary a
conditional phrasing cannot repair, so it is the one this key does not cross.

The file is signed, and **an unsigned stash is never read**. A local process running as the
user can rewrite the hook itself, so this is not a hard boundary and is not claimed as one:
it raises the bar from anyone who can write the file to anyone who can also read the API
key, which is real defence against a filesystem-only reach (a sync client, a container
mount, an editor extension). The stash is the first artefact whose contents go into a
prompt as trusted text with no server round trip to validate them, and the hook CLI is
invocable by any agent with a shell, including one under prompt injection.

That is why the absence of a credential disables the feature rather than weakening it. An
earlier version derived the key from ``api_key or ""``, reasoning that nothing resolves
without a key so there could never be a stash to forge. The reasoning was wrong twice over:
forging needs a writable path rather than a genuine stash, and the read path is gated on the
configured agent name, which is a different variable entirely. With no key the derivation
ran over an empty secret and yielded a value anyone could compute from this open-source
wheel, so any local writer could put arbitrary text into the next prompt. Signing now
requires a real credential and refuses on its absence.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Any

from hyperstruck._wire import ResolvedContext
from hyperstruck.ide.debug import debug as _debug
from hyperstruck.ide.redaction import clip_goal
from hyperstruck.env import API_KEY_ENV_VARS, first_env
from hyperstruck.ide.constants import (
    STASH_FRESHNESS_SECONDS,
    STASH_SUBDIR,
    hyper_home,
)
from hyperstruck.ide.state import read_json, safe_name, write_json_atomic

# Key separation (RFC 5869): the signing key is derived from the API key rather than being
# it, so a signature can never be replayed as, or leak, the credential that authenticates.
_HKDF_INFO = b"hyperstruck-ide-warm-stash-v1"
# The agent and the project are signed alongside the payload, not merely used to name the
# file. Without them a validly-signed stash stays valid when moved, so a stash earned in one
# project could be dropped into another and read as that project's own experience, which is
# the one boundary the declared provenance cannot repair.
_SIGNED_FIELDS = (
    "agent_name",
    "cwd",
    "goal",
    "injected_text",
    "injected_facts_text",
    "written_at",
)

_MINUTES_BEFORE_HOURS_READ_BETTER = 90


def stash_path(agent_name: str, cwd: str) -> Path:
    """Where this agent's stash for this project lives.

    Outside the session dir on purpose: ``clear_recall`` fires at both the start and the
    end of every turn, which are exactly the two moments a value has to survive.
    """
    digest = hashlib.sha256(str(cwd).encode("utf-8")).hexdigest()[:16]
    return hyper_home() / STASH_SUBDIR / f"{safe_name(agent_name)}.{digest}.json"


def sweep_expired(*, now: float | None = None) -> int:
    """Delete stashes past their window, returning how many went.

    Nothing else ever removes one, and each holds resolved advice about a project. An
    expired stash is already inert to :func:`read`, so this is about not keeping
    model-facing text on disk indefinitely rather than about correctness. Called from the
    same write that would otherwise let them accumulate, so there is no sweeper to run.
    """
    moment = time.time() if now is None else now
    removed = 0
    root = hyper_home() / STASH_SUBDIR
    if not root.is_dir():
        return 0
    for path in root.glob("*.json"):
        record = read_json(path)
        age = moment - _written_at(record if isinstance(record, dict) else {})
        if age > STASH_FRESHNESS_SECONDS:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def write(agent_name: str, cwd: str, *, goal: str, context: ResolvedContext) -> bool:
    """Publish this turn's resolve as the project's warm stash. Returns whether it did.

    Last write wins, with one rule: a resolve that returned nothing never overwrites a
    good stash. The stash is by definition the most recent useful resolve for the project,
    so fresher beats richer and no tie-break is needed, but an empty result is not fresher
    experience, it is none, and letting it land would blank the warm path.
    """
    if _signing_key() is None:
        return False
    advice = context.injected_text
    facts = context.injected_facts_text
    if not advice and not facts:
        return False
    record = {
        "agent_name": agent_name,
        "cwd": cwd,
        "goal": goal,
        "injected_text": advice,
        "injected_facts_text": facts,
        "written_at": time.time(),
    }
    record["signature"] = _sign(record)
    path = stash_path(agent_name, cwd)
    write_json_atomic(path, record)
    sweep_expired()
    return True


def read(
    agent_name: str, cwd: str, *, now: float | None = None
) -> dict[str, Any] | None:
    """This project's stash when it is fresh and intact, else nothing.

    Non-destructive, unlike the per-turn recall stash it sits beside. That one is a
    one-shot handoff to whichever parallel hook wins the claim; this one is read by every
    turn of every session working in the project, so consuming it would starve all but the
    first.
    """
    if _signing_key() is None:
        _debug("warm stash: no credential configured, so nothing can be vouched for")
        return None
    record = read_json(stash_path(agent_name, cwd))
    if not isinstance(record, dict):
        return None
    age = (time.time() if now is None else now) - _written_at(record)
    if not 0 <= age <= STASH_FRESHNESS_SECONDS:
        _debug(f"warm stash: {age / 3600:.1f}h old, past its window")
        return None
    # Compared against the agent and project asked for, not against what the file claims,
    # so a stash moved between projects fails rather than authenticating its own move.
    expected = dict(record, agent_name=agent_name, cwd=cwd)
    if not hmac.compare_digest(str(record.get("signature") or ""), _sign(expected)):
        # Reported apart from an absent stash on purpose. They look identical from the
        # emission side and mean opposite things: one is an ordinary cold project, the
        # other is a file that was written by something that could not sign it.
        _debug(
            "warm stash REFUSED: signature does not verify for this agent and project"
        )
        return None
    return dict(record, age_seconds=age)


def provenance(record: dict[str, Any]) -> str:
    """The line that demotes the stash to what it actually is.

    Without it the block reads as advice bound to this turn's goal, which is a warrant
    this client has not established and cannot check. Naming the goal it *was* checked
    against, and how long ago, lets the model discount an unrelated stash itself.
    """
    # Clipped. It is signed and server-round-tripped so it is not attacker-controlled, but it
    # is the one free-text field crossing into a prompt as trusted text, and a pathological
    # goal would otherwise dominate the block it is meant to introduce.
    goal = clip_goal(str(record.get("goal") or "").strip())
    about = f", on “{goal}”" if goal else ""
    return (
        f"From your previous turn in this project ({_age_phrase(record)}{about}). "
        "It was not checked against what you were just asked, so treat it as possibly "
        "relevant experience rather than as established guidance for this task."
    )


def _age_phrase(record: dict[str, Any]) -> str:
    minutes = max(1, round(float(record.get("age_seconds") or 0.0) / 60))
    if minutes < _MINUTES_BEFORE_HOURS_READ_BETTER:
        return f"about {minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = round(minutes / 60)
    return f"about {hours} hour{'s' if hours != 1 else ''} ago"


def _written_at(record: dict[str, Any]) -> float:
    try:
        return float(record.get("written_at") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _sign(record: dict[str, Any]) -> str:
    """Sign the fields that are read back, over a shape no field's value can forge.

    Length-prefixed rather than joined by a separator: a goal free to contain the
    separator could otherwise be written to shift a boundary and leave the digest intact
    while the parsed record differs.
    """
    key = _signing_key()
    if key is None:
        return ""
    payload = b"".join(
        _length_prefixed(str(record.get(field) or "")) for field in _SIGNED_FIELDS
    )
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _length_prefixed(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(8, "big") + raw


def _signing_key() -> bytes | None:
    """HKDF (RFC 5869) over the one credential this client holds, or nothing without it.

    Key separation is the point: the signing key is derived from the API key rather than
    being it. Returning ``None`` on an absent credential is what makes the signature mean
    something, because a key derived from an empty secret is a published constant and a
    signature under it authenticates anybody.

    Disabling the feature is the right failure: without a credential nothing resolves, so
    there is no genuine stash to show, and refusing to read one costs nothing that works.
    """
    secret = first_env(API_KEY_ENV_VARS)
    if not secret:
        return None
    extracted = hmac.new(b"", secret.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(extracted, _HKDF_INFO + b"\x01", hashlib.sha256).digest()
