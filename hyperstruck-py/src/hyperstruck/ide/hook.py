"""The IDE learning hooks: the editor-driven analogue of the LangGraph middleware.

Where the middleware runs the resolve/observe/reinforce loop inside one
``ainvoke``, these hooks run it across three separate OS processes fired by the
editor, sharing per-turn state on disk (see :mod:`hyperstruck.ide.state`):

* ``prompt`` (Claude Code ``UserPromptSubmit``; the Cursor skill calls it too):
  recovers any turn whose stop never fired, sweeps stale sessions, records the new
  active turn, and detaches its resolve.
* ``resolve`` (internal, detached): resolves the active goal into a recall stash.
* ``tool`` (``PostToolUse`` / Cursor tool hooks): appends one redacted step and,
  on the first eligible hook, atomically claims and injects the recall stash.
* ``stop`` (``Stop`` / Cursor ``stop``): labels the turn from its own evidence and
  stages it for delivery. Nothing is held for a successor turn.
* ``flush`` (internal, detached): delivers one turn's observe then reinforce.

Every command fails open: any error exits 0 with no output, so the learning loop
can never block or break the user's editing. A turn is written at its own stop and
handed to a detached ``flush`` process, so it never delays the editor and never
depends on a later event that a one-shot run will not produce.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import re

# Used only for fixed-argv detached processes; never a shell.
import subprocess  # nosec B404
import sys
import time
import uuid
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import Any

from hyperstruck._wire import (
    REASON_BELOW_MATERIAL_THRESHOLD,
    REASON_EMPTY_OFFER,
    REASON_NO_TOOL_CALLS,
    REASON_UNEVIDENCED_OUTCOME,
    EvidenceItem,
    ResolvedContext,
)
from hyperstruck.client import (
    DEFAULT_RECALL_TIMEOUT,
    HostedLearningClient,
    ResolvePurpose,
)
from hyperstruck.env import RESOLVE_TIMEOUT_ENV, env_float
from hyperstruck.identity import AgentIdentity
from hyperstruck.ide import outcome, receipt, state
from hyperstruck.ide.config import configured_agent_name, load_env
from hyperstruck.ide.debug import debug as _debug
from hyperstruck.ide.constants import (
    CREDENTIAL_HEAD_CHARS,
    DEFAULT_FLUSH_MAX_ATTEMPTS,
    DISTILL_RUN_ID_PREFIX,
    EVICTION_WINDOW_SECONDS,
    FLUSH_MAX_ATTEMPTS_ENV,
    FLUSH_STALE_SECONDS,
    HOOK_FAILURES_LOG,
    HOOK_FAILURES_LOG_MAX_BYTES,
    MAX_EPISODE_STEPS,
    MAX_RECEIPT_CHARS,
    MAX_STEP_FIELD_CHARS,
    MIN_RECALL_TIMEOUT,
    MINTED_RUN_ID_CHARS,
    MINTED_RUN_ID_TOKEN,
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STEP_FAILURE_STATUSES,
    hyper_home,
)
from hyperstruck.ide.gating import classify_tool, should_observe
from hyperstruck.ide.host_vocabularies import vocabulary_for
from hyperstruck.ide.redaction import (
    clip_goal,
    clip_result,
    redact_ide_episode,
    scrub_secrets,
)
from hyperstruck.ide.state import ActiveTurn, FinishedTurn
from hyperstruck.redaction import known_credential_match

# Wire fields of a step (the rest of a stored step, e.g. ``kind``, is client-only).
_WIRE_STEP_FIELDS = ("id", "name", "args", "status", "result", "error")
_DISTILL_EMBEDDED_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])("
    r"sk-[A-Za-z0-9_\-]{16,}"
    r"|[sr]k_(?:live|test)_[A-Za-z0-9]{10,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r")"
)


# -- command: prompt (turn start) --------------------------------------------


def cmd_prompt(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn start: record and detach resolve; recover any interrupted turn."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    # Scrubbed here, not just in redact_ide_episode: this goal also goes to
    # resolve, which the episode redaction never touches.
    # --goal is honoured only for read-only recall. On the recording path the goal must come
    # from the host's prompt payload and nothing else: it is the turn's stated intent and it
    # reaches the corpus. The installed hooks already pass stdin, but this CLI is invocable by
    # any agent with a shell, including one under prompt injection, so the restriction has to
    # live in the code rather than in which argv the installer happens to write.
    raw_goal = (args.goal if args.readonly else payload.get("prompt")) or ""
    goal = clip_goal(scrub_secrets(raw_goal.strip()))
    agent_name = configured_agent_name()

    # Read-only recall (the hyper-learning skill): resolve and print for this goal,
    # without touching any turn state, so an explicit recall never disturbs the
    # automatic loop. A throwaway run id is declined immediately so it cannot
    # sit unclosed beside the live hook run. Omitted --resolve-purpose stays
    # agent_loop so already-installed skill commands keep contributing; human
    # inspection must pass explicit_recall.
    if args.readonly:
        if agent_name:
            run_id = _new_run_id(agent_name, session_id)
            source = _source(args)
            context = _resolve(
                agent_name,
                run_id,
                goal,
                source,
                resolve_purpose=args.resolve_purpose,
            )
            _emit_injection(
                _combined_injection(context.injected_text, context.injected_facts_text),
                args,
            )
            _close_readonly_run(agent_name, run_id, context, source)
        else:
            _debug("prompt(readonly): no agent configured")
        return

    # 1. Orphan recovery: a turn interrupted before its stop hook fired never
    #    finalised. It really happened, so close it now. With no stop payload it has
    #    no native status, so it is labelled from its steps alone and declines when
    #    they say nothing, rather than being credited for having been interrupted.
    orphan = state.read_active(session_id)
    if orphan is not None:
        # An interrupted turn still showed the model its recall, and its marker is
        # already in this session's transcript, so recover the receipt here rather
        # than crediting nothing for every turn whose stop hook never fired.
        _finalise(
            session_id,
            orphan,
            state.read_steps(session_id),
            native_status=None,
            context_receipt=_acceptance_record(orphan, payload),
        )
    # 2. Sweep stale sessions (backstop delivery).
    _sweep_stale(exclude=session_id)
    # 3. No configured agent means nothing to learn into: fail open, no injection.
    if not agent_name:
        _debug("prompt: no agent configured; loop idle, nothing to resolve")
        return
    # 4. Begin the new turn, then resolve outside the editor's prompt hook.
    run_id = _new_run_id(agent_name, session_id)
    state.write_active(
        session_id,
        ActiveTurn(
            run_id=run_id,
            agent_name=agent_name,
            goal=goal,
            source_framework=_source(args),
            started_at=time.time(),
            transcript_path=str(payload.get("transcript_path") or ""),
        ),
    )
    _spawn_resolve(session_id)


# -- command: tool (capture a step) ------------------------------------------


def cmd_tool(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Append one redacted step. Lazily starts a turn if none is active.

    The lazy start keeps the write path robust on Cursor, where the resolve skill
    may not have run for this turn: steps are still captured and the turn can be
    observed at stop even without an injection.
    """
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    if args.inject:
        # Cursor postToolUse: atomically claim the detached recall, once per turn.
        # This hook does not capture a step (afterFileEdit/afterShellExecution do),
        # so injection and capture never double-count the same tool call.
        _inject_pending(session_id, SOURCE_CURSOR)
        return
    if state.read_active(session_id) is None:
        agent_name = configured_agent_name()
        if not agent_name:
            _debug("tool: no agent configured; step not captured")
            return  # no agent configured: nothing to capture into, fail open
        run_id = _new_run_id(agent_name, session_id)
        # reset_steps=False: a parallel tool hook may already have written a step
        # for this turn; resetting the steps dir would drop it.
        state.write_active(
            session_id,
            ActiveTurn(
                run_id=run_id,
                agent_name=agent_name,
                goal="",
                source_framework=_source(args),
                started_at=time.time(),
                transcript_path=str(payload.get("transcript_path") or ""),
            ),
            reset_steps=False,
        )
    state.append_step(session_id, _step_from_payload(payload, args))
    if _source(args) == SOURCE_CLAUDE_CODE:
        _inject_pending(session_id, SOURCE_CLAUDE_CODE)


# -- command: stop (finalise provisional) ------------------------------------


def cmd_stop(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn end: label this turn from its own evidence and stage it for delivery."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    active = state.read_active(session_id)
    if active is None:
        _debug("stop: no active turn for session; nothing to finalise")
        return
    steps = state.read_steps(session_id)
    native_status = args.native_status or payload.get("status")
    _finalise(
        session_id,
        active,
        steps,
        native_status=native_status,
        context_receipt=_acceptance_record(active, payload),
    )


# -- command: resolve (detached recall) --------------------------------------


def cmd_resolve(session_id: str) -> None:
    """Resolve one active turn into a tool-hook stash; fail open on every error."""
    try:
        load_env()
        active = state.read_active(session_id)
        if active is None:
            _debug("resolve: no active turn for session")
            return
        if not active.goal:
            _debug("resolve skipped: empty goal")
            return
        context = asyncio.run(
            _aresolve(
                active.agent_name,
                active.run_id,
                active.goal,
                source_framework=active.source_framework or SOURCE_CLAUDE_CODE,
            )
        )
        if not _combined_injection(context.injected_text, context.injected_facts_text):
            # An empty stash can never validate for injection; publishing it
            # would only leave dead weight for the tool hooks to skip.
            _debug("resolve dropped: no learnings to inject")
            return
        current = state.read_active(session_id)
        if current is None or current.run_id != active.run_id:
            _debug("resolve dropped: active turn changed before recall was ready")
            return
        state.write_recall(
            session_id,
            {
                "run_id": active.run_id,
                "injected_text": context.injected_text,
                "injected_facts_text": context.injected_facts_text,
                "offered_learning_ids": list(context.offered_learning_ids),
                "offered_claim_ids": list(context.offered_claim_ids),
            },
        )
        _debug(
            f"resolve ok: {len(context.offered_learning_ids)} learning(s), "
            f"{len(context.offered_claim_ids)} claim(s) for agent {active.agent_name}"
        )
    except Exception as exc:  # noqa: BLE001 - detached recall always fails open
        _debug(f"resolve failed ({type(exc).__name__}): {exc}")


# -- command: distill (caller-driven corpus extraction) ----------------------


def cmd_distill(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Distill durable learnings from a referenced corpus into the boundary agent.

    Unlike the automatic loop this is skill-driven: a referenced document, an MCP
    result, or a large tool output that carries reusable, *contrasting* knowledge
    (a design doc, a spec, a diff, a post-mortem) is handed in as a small JSON spec
    on stdin ``{goal, evidence: [{id, content, role, status, label?, source_ref?}],
    outcome?, evaluation?, run_id?}``. Identity is the configured boundary agent
    name (``HYPER_LEARNING_AGENT_NAME`` then ``HYPER_AGENT_NAME``) so a distilled
    learning lands in the same corpus the loop reads from; there is no
    repo-derived agent here.

    All caller-supplied strings are secret-scrubbed before they leave the machine
    because the server stores evidence verbatim as the grounding source. Contrast
    is required (differing ``status``, a ``contrast``/``support`` pair, or an
    ``evaluation`` note); a corpus without declared contrast is rejected locally.
    """
    parse_error = payload.get("_hyper_parse_error")
    if parse_error:
        _emit_distill_result({"status": "skipped", "reason": str(parse_error)}, args)
        return
    agent_name = configured_agent_name()
    if not agent_name:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "no agent configured (set HYPER_LEARNING_AGENT_NAME or "
                    "HYPER_AGENT_NAME)"
                ),
            },
            args,
        )
        return
    raw_goal = args.goal if args.goal is not None else payload.get("goal")
    goal = raw_goal.strip() if isinstance(raw_goal, str) else ""
    if not goal:
        _emit_distill_result(
            {"status": "skipped", "reason": "distill requires a non-empty goal"},
            args,
        )
        return
    evidence, complaints = _evidence_from_spec(payload.get("evidence"))
    if complaints:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "distill refused a corpus it could not use as given: "
                    + "; ".join(complaints)
                    + ". Nothing was sent, so fix these and retry on the same run id."
                ),
            },
            args,
        )
        return
    if len(evidence) < 2:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": "distill needs at least 2 contrasting evidence items",
            },
            args,
        )
        return
    rejection = _distill_run_id_rejection(
        payload.get("run_id")
    ) or _evidence_credential_rejection(evidence)
    if rejection:
        _emit_distill_result({"status": "skipped", "reason": rejection}, args)
        return
    run_id = _distill_run_id(payload.get("run_id"))
    outcome_spec = (
        payload.get("outcome") if isinstance(payload.get("outcome"), dict) else {}
    )
    evaluation = payload.get("evaluation")
    scrubbed_evaluation = (
        _scrub_distill_string(evaluation.strip())
        if isinstance(evaluation, str) and evaluation.strip()
        else None
    )
    if not _has_distill_contrast(evidence, scrubbed_evaluation):
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "distill requires declared contrast (different statuses, "
                    "contrast/support roles, or evaluation)"
                ),
            },
            args,
        )
        return
    try:
        result = asyncio.run(
            _adistill(
                agent_name=agent_name,
                run_id=run_id,
                goal=_scrub_distill_string(goal),
                evidence=evidence,
                outcome_spec=outcome_spec,
                evaluation=scrubbed_evaluation,
            )
        )
    except Exception as exc:  # noqa: BLE001 - caller-driven, fail with a clear message
        _debug(f"distill failed ({type(exc).__name__}): {exc}")
        result = {
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
            "agent": agent_name,
            "run_id": run_id,
        }
    _emit_distill_result(result, args)


def _evidence_from_spec(raw: Any) -> tuple[list[EvidenceItem], list[str]]:
    """Build ``EvidenceItem``s from the skill's spec, plus what could not be used.

    Returns the complaints rather than swallowing them. A dropped item changes
    what is learned and a coerced ``status`` can invert it, since status is one of
    the three signals establishing contrast, so neither may pass silently: that is
    the same silent-discard failure this whole path was rewritten to end.
    """
    if not isinstance(raw, list):
        return [], ["evidence must be a list"]
    items: list[EvidenceItem] = []
    complaints: list[str] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            complaints.append(f"evidence[{index}] is not an object")
            continue
        content = entry.get("content")
        if not isinstance(content, str) or not content.strip():
            complaints.append(f"evidence[{index}] has no content")
            continue
        role = entry.get("role")
        status = entry.get("status")
        if role is not None and role not in ("support", "contrast", "neutral"):
            complaints.append(
                f"evidence[{index}].role {role!r} is not "
                "'support', 'contrast' or 'neutral'"
            )
        if status is not None and status not in ("completed", "failed"):
            complaints.append(
                f"evidence[{index}].status {status!r} is not 'completed' or 'failed'"
            )
        source_ref = entry.get("source_ref")
        items.append(
            EvidenceItem(
                # id and source_ref are identifiers and are never rewritten; they
                # are refused instead, by _evidence_credential_rejection.
                id=str(entry.get("id") or f"e{index + 1}"),
                content=_scrub_distill_string(content),
                label=_scrub_distill_string(str(entry.get("label") or "")),
                role=role if role in ("support", "contrast", "neutral") else "neutral",
                status=status if status in ("completed", "failed") else "completed",
                source_ref=str(source_ref) if source_ref else None,
            )
        )
    return items, complaints


def _scrub_distill_string(text: str) -> str:
    """Scrub distill corpus strings, including secrets embedded in labels/URLs."""
    return _DISTILL_EMBEDDED_SECRET_PATTERN.sub("[REDACTED]", scrub_secrets(text))


def _has_distill_contrast(evidence: list[Any], evaluation: str | None) -> bool:
    """Whether the corpus declares enough contrast for the server to accept it."""
    if evaluation:
        return True
    statuses = {item.status for item in evidence}
    if len(statuses) > 1:
        return True
    roles = {item.role for item in evidence}
    return {"contrast", "support"}.issubset(roles)


def _distill_run_id_rejection(provided: Any) -> str | None:
    """Why this run id cannot be accepted, or ``None`` when it is fine.

    A run id is an opaque identifier, never free text, so it is never rewritten.
    The secret scrubber keys on high entropy in a long token, which is precisely
    the property a descriptive identifier has by design, so it cannot separate a
    leaked credential from one: measured, ``sk-proj-AbCdEf0123456789AbCdEf0123456789AbCdEf``
    is 4.43 bits/char and ``pr-305-review-round-2-fixes-and-followups`` is 4.09,
    both over the 3.5 gate.
    Running it over identifiers is a category error, and the episode path already
    says so, scrubbing only goal and steps and "never identifiers" because a
    corrupted ``run_id`` silently breaks the server's dedup.

    Refusing is stronger than rewriting on every axis that matters. Nothing
    suspect egresses at all rather than egressing in derived form, the caller
    keeps an id they can correlate with their own run, and the failure is loud
    instead of silent.

    The judgement is ``known_credential_match``, not the full scrubber. Asking the
    scrubber "would you change this?" reinstates the entropy arm that this
    docstring rejects, one layer down: it refuses every descriptive id of 32+
    characters, which is the population the refusal exists to serve.
    """
    return _identifier_credential_rejection(
        provided,
        "run id",
        "Pass a run id carrying no secret, or omit run_id entirely and one will "
        "be minted for you.",
    )


def _identifier_credential_rejection(
    provided: Any, field: str, remedy: str
) -> str | None:
    """Why this identifier cannot be accepted, or ``None`` when it is fine.

    Shared by every field whose meaning *is* its value. Redaction replaces many
    inputs with one marker, and a many-to-one map over a key manufactures
    collisions, which is the whole of the 2026-07-24 incident rather than a
    property of that one field. So an identifier is judged and refused, never
    rewritten, and the caller keeps something they can correlate.
    """
    if not (isinstance(provided, str) and provided.strip()):
        return None
    match = known_credential_match(provided.strip())
    if match is None:
        return None
    return (
        f"{field} contains {_describe_credential_match(match)}, which reads as a "
        "credential, so it was refused rather than rewritten (rewriting an "
        f"identifier is many-to-one, so it would silently collide). {remedy}"
    )


def _evidence_credential_rejection(evidence: list[EvidenceItem]) -> str | None:
    """Why this corpus cannot be accepted, or ``None`` when it is fine.

    ``id`` and ``source_ref`` are identifiers, not prose: the first keys a step
    and the second is documented in the API as "non-secret provenance: a doc id or
    URL". Scrubbing them collapsed distinct ids onto one marker and shredded the
    citation a distilled learning rests on. ``label`` and ``content`` stay
    scrubbed, because a redacted span still reads as what it was.
    """
    for index, item in enumerate(evidence):
        for field, value in (
            (f"evidence[{index}].id", item.id),
            (f"evidence[{index}].source_ref", item.source_ref),
        ):
            reason = _identifier_credential_rejection(
                value, field, "Pass provenance carrying no secret."
            )
            if reason:
                return reason
    return None


def _describe_credential_match(match: str) -> str:
    """Name the offending run-id substring without echoing a real secret.

    Only the prefix is shown, which is the part that identifies the shape and
    carries no key material. Never widen this, and never add a branch that returns
    the match whole: the argument is the suspect text itself.
    """
    return f"'{match[:CREDENTIAL_HEAD_CHARS]}...' ({len(match)} characters)"


def _distill_run_id(provided: Any) -> str:
    """Namespace the caller's run id with ``distill:`` (minted if absent).

    Deliberately never scrubbed; see :func:`_distill_run_id_rejection`.
    """
    original = provided.strip() if isinstance(provided, str) else ""
    if not original:
        return f"{DISTILL_RUN_ID_PREFIX}{MINTED_RUN_ID_TOKEN}{uuid.uuid4().hex[:MINTED_RUN_ID_CHARS]}"
    return (
        original
        if original.startswith(DISTILL_RUN_ID_PREFIX)
        else f"{DISTILL_RUN_ID_PREFIX}{original}"
    )


def _distill_success(value: Any) -> bool:
    """Coerce an optional JSON success flag without treating "false" as truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return True


async def _adistill(
    *,
    agent_name: str,
    run_id: str,
    goal: str,
    evidence: list[Any],
    outcome_spec: dict[str, Any],
    evaluation: str | None,
) -> dict[str, Any]:
    """Ship one distill job and drain it; return a compact, printable result."""
    from hyperstruck._wire import DistillOutcome
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    try:
        client = HostedLearningClient()
    except ValueError:
        return {
            "status": "skipped",
            "reason": "no API key configured",
            "agent": agent_name,
        }
    summary = outcome_spec.get("summary")
    outcome_obj = DistillOutcome(
        is_success=_distill_success(outcome_spec.get("is_success", True)),
        summary=_scrub_distill_string(str(summary)) if summary else None,
    )
    closed = False
    try:
        await client.distill(
            identity=AgentIdentity(agent_name=agent_name),
            run_id=run_id,
            goal=goal,
            evidence=evidence,
            outcome=outcome_obj,
            evaluation=evaluation,
        )
        await client.drain()
        await client.aclose()
        closed = True
        if client.writes_duplicated:
            return {
                "status": "skipped",
                "reason": (
                    "this run id was already distilled, so nothing was extracted; "
                    "use a new run id to distil this corpus again"
                ),
                "agent": agent_name,
                "run_id": run_id,
            }
        if client.writes_delivered:
            return {
                "status": "delivered",
                "agent": agent_name,
                "run_id": run_id,
                "evidence_count": len(evidence),
            }
        if client.writes_failed:
            return {
                "status": "error",
                "reason": client.last_write_error or "delivery failed",
                "agent": agent_name,
                "run_id": run_id,
            }
        return {
            "status": "pending",
            "reason": "write still in flight after the drain timeout",
            "agent": agent_name,
            "run_id": run_id,
            "evidence_count": len(evidence),
        }
    finally:
        if not closed:
            await client.aclose(drain_timeout=0)


def _emit_distill_result(result: dict[str, Any], args: argparse.Namespace) -> None:
    """Print the distill result: human text for the skill, JSON otherwise."""
    if args.emit != "text":
        json.dump(result, sys.stdout)
        return
    if result.get("status") == "delivered":
        sys.stdout.write(
            f"Distill delivered for agent '{result['agent']}' "
            f"(run {result['run_id']}, {result['evidence_count']} evidence items). "
            "Extraction runs server-side and may still yield zero learnings if "
            "the accepted corpus has no real reusable contrast.\n"
        )
        return
    if result.get("status") == "pending":
        sys.stdout.write(
            f"Distill pending for agent '{result['agent']}' "
            f"(run {result['run_id']}): {result.get('reason', '')}.\n"
        )
        return
    sys.stdout.write(f"Distill {result.get('status')}: {result.get('reason', '')}\n")


# -- command: flush (detached delivery) --------------------------------------


class FlushOutcome(Enum):
    """What one delivery attempt established about a staged flush.

    DELIVERED and UNRECOVERABLE (malformed payload / no key) both mean drop now.
    TERMINAL (a 4xx: the payload is bad) counts toward the retry cap; TRANSIENT
    (5xx / network) is retried later without counting, so a passing outage never
    drops a still-deliverable episode.
    """

    DELIVERED = "delivered"
    UNRECOVERABLE = "unrecoverable"
    TERMINAL = "terminal"
    TRANSIENT = "transient"


def cmd_flush(args: argparse.Namespace) -> None:
    """Deliver one staged turn: observe (if gated in) then reinforce.

    The staged file is removed on success, on an unrecoverable payload, and once a
    *terminal* (4xx) rejection has recurred up to the retry cap. A *transient*
    failure (boundary down, network error) leaves the file in place so the next
    sweep retries it, bounded only by the eviction window: this keeps the staging
    dir a real outbox that never discards a still-deliverable episode over a blip.
    """
    payload = state.read_flush(args.flush_path)
    if not payload:
        state.remove_flush(args.flush_path)
        return
    try:
        outcome_, cause = asyncio.run(_deliver(payload))
    except Exception as exc:  # noqa: BLE001 - fail open; treat as transient and retry
        outcome_, cause = FlushOutcome.TRANSIENT, f"{type(exc).__name__}: {exc}"
    if outcome_ in (FlushOutcome.DELIVERED, FlushOutcome.UNRECOVERABLE):
        state.remove_flush(args.flush_path)
        return
    if outcome_ is FlushOutcome.TRANSIENT:
        return  # leave staged for a later sweep; eviction is the ultimate backstop
    attempts = state.record_flush_attempt(args.flush_path)
    if attempts is None:
        return  # another flush process delivered and removed the staged file
    if attempts >= _max_flush_attempts():
        state.record_dropped_flush(
            args.flush_path,
            run_id=_staged_run_id(payload),
            agent_name=payload.get("agent_name") or payload.get("agent_id", ""),
            attempts=attempts,
            cause=cause,
        )
        state.remove_flush(args.flush_path)


# -- turn finalisation / flush staging ---------------------------------------


def _finalise(
    session_id: str,
    current: ActiveTurn,
    current_steps: list[dict[str, Any]],
    *,
    native_status: str | None,
    context_receipt: str | None = None,
) -> None:
    """Label this turn from its own evidence and deliver it now.

    Nothing is held for a successor. A turn whose evidence supports no label is
    declined rather than credited, so there is nothing left for a later turn to
    retract, and a run that has no successor by construction (a headless one-shot,
    or the last turn of any session) still closes its loop at its only stop.
    """
    turn_outcome = outcome.provisional_outcome(
        current_steps,
        native_status,
        vocabulary_for(current.source_framework),
    )
    _stage_and_flush(
        session_id,
        FinishedTurn(
            run_id=current.run_id,
            agent_name=current.agent_name,
            goal=current.goal,
            steps=tuple(current_steps),
            source_framework=current.source_framework,
            ended_at=time.time(),
            offered_learning_ids=current.offered_learning_ids,
            offered_claim_ids=current.offered_claim_ids,
            is_injected=current.is_injected,
            context_receipt=context_receipt or "",
        ),
        turn_outcome,
    )
    state.retire_active(session_id)


def _transcript_path(payload: dict[str, Any], turn: ActiveTurn) -> str:
    """Where to look for this turn's acceptance record.

    The live payload wins where there is one: a session that was resumed into a new
    transcript file keeps writing to the current path, and the turn's stored path is
    then the stale one. The stored path is what the backstop sweep has, since it
    finalises another session's abandoned turn from a payload that is not about it.
    """
    return str(payload.get("transcript_path") or turn.transcript_path or "")


def _acceptance_record(turn: ActiveTurn, payload: dict[str, Any] | None = None) -> str:
    """This turn's receipt, or nothing when there is provably none to find.

    A turn that never injected stamped no marker, so the transcript cannot hold an
    acceptance record for it and the read is a guaranteed miss over a file that grows
    with the session. Skipping it also keeps a turn that offered nothing from posting an
    empty receipt, which the boundary would otherwise have to warn about.
    """
    if not turn.is_injected:
        return ""
    return receipt.acceptance_record(_transcript_path(payload or {}, turn), turn.run_id)


def _clipped_receipt(receipt_text: str) -> str | None:
    """Scrub the receipt, then bound it without pretending the evidence is complete.

    The receipt is a slice of the editor's own transcript, so it is user content and
    gets the same scrubbing every other outbound field gets, not an exemption for being
    matched rather than stored. Scrubbing before clipping, because a redaction changes
    the length. It can in principle cost a rule its match, if the rule's own text looks
    like a credential; that trade goes to privacy.

    ``MAX_RECEIPT_CHARS`` sits ABOVE the boundary's own ceiling, so a receipt clipped
    here still arrives over-cap and the server engages its confirm-only lane: it credits
    what it can match and demotes nothing, because a payload it had to cut says nothing
    about what is missing from it. Clipping to a lower cap would deliver a truncated
    receipt that reads as a complete account, and every rule past the cut would be
    recorded UNEXPOSED, which is terminal. The marker leads what survives, so the
    receipt still resolves to this run.
    """
    if not receipt_text:
        return None
    scrubbed = scrub_secrets(receipt_text)
    if len(scrubbed) <= MAX_RECEIPT_CHARS:
        return scrubbed
    _debug(f"receipt clipped from {len(scrubbed)} to {MAX_RECEIPT_CHARS} chars")
    return scrubbed[:MAX_RECEIPT_CHARS]


def _stage_and_flush(
    session_id: str, pending: FinishedTurn, turn_outcome: outcome.TurnOutcome
) -> None:
    """Gate, stage the redacted episode with its label, detach a flush.

    An unevidenced turn never reaches the episode path however material it was.
    Observing it would have to assert an outcome, and the only assertion available
    would be a guess; declining closes the run, credits nothing, and asserts
    nothing, which is what the outcome ladder abstained for.
    """
    if not pending.agent_name:
        return  # nothing to deliver to (turn captured before an agent was set)
    steps = list(pending.steps)
    # An observed turn that offered nothing still closes its loop server-side, so
    # reinforce it too; skipping empty offers is what left those runs half-open. A
    # trivial turn (no material steps, no offer) still short-circuits below.
    offered = bool(pending.offered_learning_ids) or bool(pending.offered_claim_ids)
    is_worth_learning_from = should_observe(steps) or offered
    do_observe = turn_outcome.is_evidenced and should_observe(steps)
    do_reinforce = do_observe or (turn_outcome.is_evidenced and offered)
    if not (do_observe or do_reinforce):
        # Not worth learning from, but the run it opened is still open server-side,
        # and going quiet made a deliberate skip look identical to a broken host.
        # Staged like any other write so it inherits retry and drop accounting.
        staged_decline = {
            "agent_name": pending.agent_name,
            "decline": {
                "run_id": pending.run_id,
                "reason": _decline_reason(steps, is_worth_learning_from),
                "is_delivered": pending.is_injected,
                "source_framework": pending.source_framework,
            },
        }
        _spawn_flush(state.stage_flush(session_id, pending.run_id, staged_decline))
        return
    episode = _build_episode(pending, turn_outcome.is_success)
    staged = {
        "agent_name": pending.agent_name,
        "episode": redact_ide_episode(episode),
        "do_observe": do_observe,
        "do_reinforce": do_reinforce,
        "context_receipt": _clipped_receipt(pending.context_receipt),
    }
    path = state.stage_flush(session_id, pending.run_id, staged)
    _spawn_flush(path)


def _staged_run_id(payload: dict[str, Any]) -> str:
    """The run a staged payload belongs to, whichever kind of write it carries.

    A dropped write is the one record that survives the loss, so it is worthless
    without the run id: an unattributable drop is exactly the silent hole a decline
    exists to close. Episodes and declines nest the id differently, so read both.
    """
    for block in ("episode", "decline"):
        nested = payload.get(block)
        if isinstance(nested, dict) and nested.get("run_id"):
            return str(nested["run_id"])
    return ""


def _decline_reason(steps: list[dict[str, Any]], is_worth_learning_from: bool) -> str:
    """Why this turn was declined, from the gate that actually decided it.

    Derived rather than invented, so the reported cause and the gate can never
    disagree. This is what makes the gate measurable: until now it fired silently,
    so how often it skipped a turn, and why, was invisible.

    The missing outcome is reported only for a turn the step gates would have let
    through, because that is the only case where it decided anything. A read-only
    turn is below the material threshold whatever its evidence says, and naming the
    outcome there would report a gate that never got to run.

    The wire contract also carries ``empty_offer`` for callers whose recall returned
    nothing to apply. This host cannot reach it: an empty offer with material steps
    still observes, and one without them is already described by the step count.
    """
    if is_worth_learning_from:
        return REASON_UNEVIDENCED_OUTCOME
    return REASON_NO_TOOL_CALLS if not steps else REASON_BELOW_MATERIAL_THRESHOLD


def _build_episode(pending: FinishedTurn, is_success: bool) -> dict[str, Any]:
    """Project stored steps onto the wire episode shape (drops client-only fields)."""
    # Keep the tail when a turn overruns the boundary's cap: the trailing steps
    # carry the outcome the producer reads. The counts stay over the full turn.
    wire_steps = [
        {field: step.get(field) for field in _WIRE_STEP_FIELDS}
        for step in pending.steps[-MAX_EPISODE_STEPS:]
    ]
    completed = sum(
        1 for step in pending.steps if step.get("status") == STATUS_COMPLETED
    )
    failed = sum(1 for step in pending.steps if step.get("status") == STATUS_FAILED)
    return {
        "run_id": pending.run_id,
        "goal": pending.goal,
        "steps": wire_steps,
        "outcome": {
            "is_success": is_success,
            "total_steps": len(pending.steps),
            "completed_steps": completed,
            "failed_steps": failed,
        },
        "source_framework": pending.source_framework,
        "thread_id": None,
    }


def _sweep_stale(*, exclude: str) -> None:
    """Recover turns no stop hook ever closed, and drain the previous release's pending.

    Two jobs, not one. The orphan branch recovers a turn from a session that died
    before ``Stop`` fired: it has no stop payload, therefore no native status, so it
    is unevidenced by definition and is declined. That is the honest outcome for a
    crashed turn and it is what this sweep always reached for.

    ``exclude`` protects the caller's own *live* turn from being swept out from under
    it. It deliberately does not cover the drain below: a pending file cannot belong to
    a live turn, because nothing in this release writes one, and the session holding it
    is usually the very session the user upgraded in the middle of. Excluding that one
    would strand the commonest case until the user happened to open a different session.

    TODO(ceiling): the drain reads ``pending.json`` files written by the release before
    this one, on the boolean label that file recorded. Remove it, and
    ``state.read_pending`` with it, one release after this ships.
    """
    now = time.time()
    for session_id in state.all_session_ids():
        _drain_previous_release_pending(session_id)
        if session_id == exclude:
            continue
        orphan = state.read_active(session_id)
        if orphan is not None and now - orphan.started_at > EVICTION_WINDOW_SECONDS:
            _finalise(
                session_id,
                orphan,
                state.read_steps(session_id),
                native_status=None,
                context_receipt=_acceptance_record(orphan),
            )
        elif orphan is None:
            state.clear_recall(session_id)
        _recover_flushes(session_id, now)
        state.remove_session_if_empty(session_id)


def _drain_previous_release_pending(session_id: str) -> None:
    """Deliver a turn the previous release deferred to disk, on the label it recorded.

    Not re-derived from the turn's steps: that file is the older code's verdict on a
    turn this code never saw end, and re-labelling it would apply a stricter rule to
    evidence gathered under a looser one.
    """
    deferred = state.read_pending(session_id)
    if deferred is None:
        return
    turn, is_success = deferred
    _stage_and_flush(
        session_id,
        turn,
        outcome.TurnOutcome.SUCCESS if is_success else outcome.TurnOutcome.FAILURE,
    )
    state.clear_pending(session_id)


def _recover_flushes(session_id: str, now: float) -> None:
    """Re-deliver or evict flush files orphaned by a killed flush process.

    A detached flush removes its file on completion; one left behind means its
    process died (sleep, OOM, reboot) before delivering. Re-spawn a flush for it
    (at-least-once is safe, the platform dedups by run id), but evict files past
    the eviction window so a permanently-failing delivery cannot pin the session.
    """
    for path in state.iter_flush_files(session_id):
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age > EVICTION_WINDOW_SECONDS:
            state.remove_flush(path)  # never delivered in time; drop it
        elif age > FLUSH_STALE_SECONDS:
            _spawn_flush(path)  # presumed orphaned; retry. Younger files are in flight.


def _max_flush_attempts() -> int:
    """Configured outer flush attempts; the HTTP client still retries per attempt."""
    raw = os.environ.get(FLUSH_MAX_ATTEMPTS_ENV)
    if raw is None:
        return DEFAULT_FLUSH_MAX_ATTEMPTS
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_FLUSH_MAX_ATTEMPTS
    return max(1, parsed)


# -- network (resolve / deliver) ---------------------------------------------


def _recall_timeout() -> float:
    """Seconds a hook recall waits.

    Floored, because a zero or negative override reproduces the original defect:
    every recall times out and fails open as though the corpus were empty.
    """
    return max(
        MIN_RECALL_TIMEOUT, env_float(RESOLVE_TIMEOUT_ENV, DEFAULT_RECALL_TIMEOUT)
    )


def _empty_context() -> ResolvedContext:
    return ResolvedContext()


def _resolve(
    agent_name: str,
    run_id: str,
    goal: str,
    source_framework: str,
    *,
    resolve_purpose: ResolvePurpose = ResolvePurpose.AGENT_LOOP,
) -> ResolvedContext:
    """Resolve the goal's learnings and claims. Fails open to an empty context."""
    if not goal:
        _debug("resolve skipped: empty goal")
        return _empty_context()
    try:
        context = asyncio.run(
            _aresolve(
                agent_name,
                run_id,
                goal,
                source_framework=source_framework,
                resolve_purpose=resolve_purpose,
            )
        )
        _debug(
            f"resolve ok: {len(context.offered_learning_ids)} learning(s), "
            f"{len(context.offered_claim_ids)} claim(s) for agent {agent_name}"
        )
        return context
    except TimeoutError:
        print(
            f"[hyperstruck] recall timed out after {_recall_timeout():g}s; "
            "proceeding without learnings",
            file=sys.stderr,
        )
        return _empty_context()
    except Exception as exc:  # noqa: BLE001 - explicit recall always fails open
        _debug(f"resolve failed ({type(exc).__name__}): {exc}")
        return _empty_context()


async def _aresolve(
    agent_name: str,
    run_id: str,
    goal: str,
    *,
    source_framework: str = SOURCE_CLAUDE_CODE,
    resolve_timeout: float | None = None,
    resolve_purpose: ResolvePurpose = ResolvePurpose.AGENT_LOOP,
) -> ResolvedContext:
    client = HostedLearningClient(
        resolve_timeout=(
            _recall_timeout() if resolve_timeout is None else resolve_timeout
        ),
        client_host=source_framework,
    )
    try:
        return await client.resolve(
            identity=AgentIdentity(agent_name=agent_name),
            run_id=run_id,
            goal=goal,
            source_framework=source_framework,
            resolve_purpose=resolve_purpose,
        )
    finally:
        await client.aclose()


def _readonly_decline_payload(
    run_id: str, context: ResolvedContext, source_framework: str
) -> dict[str, Any]:
    offered = bool(context.offered_learning_ids) or bool(context.offered_claim_ids)
    return {
        "run_id": run_id,
        "reason": (REASON_BELOW_MATERIAL_THRESHOLD if offered else REASON_EMPTY_OFFER),
        "is_delivered": bool(
            _combined_injection(context.injected_text, context.injected_facts_text)
        ),
        "source_framework": source_framework,
    }


def _close_readonly_run(
    agent_name: str, run_id: str, context: ResolvedContext, source_framework: str
) -> None:
    """Decline a skill-driven throwaway recall so it cannot sit unclosed."""
    try:
        asyncio.run(
            _deliver_decline(
                agent_name,
                _readonly_decline_payload(run_id, context, source_framework),
            )
        )
    except Exception as exc:  # noqa: BLE001 - readonly close always fails open
        _debug(f"readonly decline failed ({type(exc).__name__}): {exc}")


def _combined_injection(advice: str | None, facts: str | None) -> str | None:
    """Place the advice and fact blocks adjacently when the host wants no choice."""
    parts = [block for block in (advice, facts) if block]
    if not parts:
        return None
    return "\n\n".join(parts)


async def _deliver_decline(
    agent_name: str, decline: dict[str, Any]
) -> tuple[FlushOutcome, str | None]:
    """Close a run the gate declined. Same outcome taxonomy as an episode write."""
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    run_id = decline.get("run_id")
    reason = decline.get("reason")
    if not run_id or not reason:
        return FlushOutcome.UNRECOVERABLE, "malformed staged decline"
    try:
        client = HostedLearningClient(
            client_host=str(decline.get("source_framework") or SOURCE_CLAUDE_CODE)
        )
    except ValueError:
        return FlushOutcome.UNRECOVERABLE, "no API key configured"
    try:
        await client.decline(
            identity=AgentIdentity(agent_name=agent_name),
            run_id=run_id,
            reason=reason,
            is_delivered=bool(decline.get("is_delivered")),
            source_framework=decline.get("source_framework", SOURCE_CLAUDE_CODE),
        )
        await client.drain()
        if client.writes_failed == 0:
            return FlushOutcome.DELIVERED, None
        if client.writes_terminal_failed:
            return FlushOutcome.TERMINAL, client.last_write_error
        return FlushOutcome.TRANSIENT, client.last_write_error
    finally:
        await client.aclose()


async def _deliver(payload: dict[str, Any]) -> tuple[FlushOutcome, str | None]:
    """Observe (awaited to completion) then reinforce, so the wire order holds.

    Returns the outcome plus a coarse cause tag. A 4xx rejection is TERMINAL (the
    payload is bad, so it counts toward the retry cap); a 5xx/network failure is
    TRANSIENT (retry later, uncounted); a malformed payload or missing key is
    UNRECOVERABLE (drop now, retrying cannot help).
    """
    from hyperstruck._wire import Episode, StepRecord, TerminalOutcome
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    agent_name = payload.get("agent_name") or payload.get("agent_id")
    decline_data = payload.get("decline")
    if agent_name and decline_data:
        return await _deliver_decline(agent_name, decline_data)
    episode_data = payload.get("episode") or {}
    if not agent_name or not episode_data:
        return FlushOutcome.UNRECOVERABLE, "malformed staged payload"
    identity = AgentIdentity(agent_name=agent_name)
    outcome_data = episode_data.get("outcome") or {}
    episode = Episode(
        run_id=episode_data.get("run_id", ""),
        goal=episode_data.get("goal", ""),
        steps=tuple(
            StepRecord(**_wire_step(step)) for step in episode_data.get("steps") or []
        ),
        outcome=TerminalOutcome(
            is_success=bool(outcome_data.get("is_success", True)),
            total_steps=int(outcome_data.get("total_steps", 0)),
            completed_steps=int(outcome_data.get("completed_steps", 0)),
            failed_steps=int(outcome_data.get("failed_steps", 0)),
        ),
        source_framework=episode_data.get("source_framework", SOURCE_CLAUDE_CODE),
        # Rebuilt field by field, so anything omitted here is staged, scrubbed, written to
        # disk and then silently dropped at the moment of delivery. That is how the utterance
        # came to be plumbed through five layers and never transmitted; thread_id had the same
        # omission already. Keep this list in step with _build_episode.
        principal_utterance=episode_data.get("principal_utterance"),
        thread_id=episode_data.get("thread_id"),
    )
    try:
        client = HostedLearningClient(
            client_host=str(episode_data.get("source_framework") or SOURCE_CLAUDE_CODE)
        )
    except ValueError:
        return FlushOutcome.UNRECOVERABLE, "no API key configured"
    try:
        if payload.get("do_observe"):
            await client.observe(identity=identity, episode=episode)
            await client.drain()  # land observe before reinforce reads its offer log
        if payload.get("do_reinforce"):
            # IDE tool calls are undeclared, so an IDE turn never auto-promotes.
            await client.reinforce(
                identity=identity,
                episode=episode,
                is_org_promotion_allowed=False,
                context_receipt=payload.get("context_receipt"),
            )
            await client.drain()
        # The client retries internally then drops with a counter rather than
        # raising. A terminal (4xx) failure means the payload is bad and will fail
        # every retry, so it counts toward the cap; a transient failure keeps the
        # staged file for the next sweep without counting.
        if client.writes_failed == 0:
            return FlushOutcome.DELIVERED, None
        if client.writes_terminal_failed:
            return FlushOutcome.TERMINAL, client.last_write_error
        return FlushOutcome.TRANSIENT, client.last_write_error
    finally:
        await client.aclose()


def _wire_step(step: dict[str, Any]) -> dict[str, Any]:
    """Keep only StepRecord's fields, with a non-empty id (StepRecord requires it)."""
    wire = {field: step.get(field) for field in _WIRE_STEP_FIELDS}
    if not wire.get("id"):
        wire["id"] = uuid.uuid4().hex
    if not wire.get("name"):
        wire["name"] = "tool"
    for field in ("id", "name"):
        wire[field] = str(wire[field])[:MAX_STEP_FIELD_CHARS]
    if wire.get("status") not in (STATUS_COMPLETED, STATUS_FAILED):
        wire["status"] = STATUS_COMPLETED
    if not isinstance(wire.get("args"), dict):
        wire["args"] = {}
    return wire


# -- step capture ------------------------------------------------------------


def _step_from_payload(
    payload: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Build a redacted, no-raw-content step from a tool-hook payload.

    Spans Claude Code (``tool_name``/``tool_input``/``tool_response``) and Cursor
    (``command``/``file_path``/``exit_code``) shapes. Only safe-to-ship inputs go
    in ``args`` (path, command); no file body, diff, or tool output is ever
    captured. The result is always dropped (it would be source); only the tool
    name, path/command, status, and a clipped, scrubbed error survive.
    """
    name = (
        args.name
        or payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or "tool"
    )
    kind = args.kind or classify_tool(name)

    safe_args: dict[str, Any] = {}
    path = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("file_path")
    )
    if path:
        safe_args["path"] = scrub_secrets(str(path))
    command = payload.get("command") or (payload.get("tool_input") or {}).get("command")
    if command:
        safe_args["command"] = scrub_secrets(clip_result(command))

    is_error = _is_error(payload)
    # No tool result is ever shipped. A read or edit result is file contents or a
    # diff, and a command's stdout can be source too (git diff, grep, cat). The
    # only execution signal we need is pass/fail (the status); the failure detail
    # rides in `error`, clipped and scrubbed. So `result` is always dropped.
    raw_error = payload.get("error") or payload.get("stderr")
    response = payload.get("tool_response")
    if not raw_error and isinstance(response, dict):
        raw_error = response.get("stderr") or response.get("error")

    return {
        "id": payload.get("tool_call_id") or payload.get("id") or uuid.uuid4().hex,
        "name": str(name),
        "args": safe_args,
        "status": STATUS_FAILED if is_error else STATUS_COMPLETED,
        "result": None,
        "error": (
            scrub_secrets(clip_result(raw_error)) if (is_error and raw_error) else None
        ),
        "kind": kind,
    }


def _is_error(payload: dict[str, Any]) -> bool:
    """Whether a tool call failed, across Claude Code and Cursor payload shapes.

    Claude Code's ``Bash`` failures surface inside ``tool_response`` (stderr /
    interrupted / a nested exit code), not as a top-level field, so the nested
    dict is inspected as well as the top level.
    """
    if _failed_exit(payload.get("exit_code")):
        return True
    if payload.get("is_error") or payload.get("error") or payload.get("stderr"):
        return True
    if str(payload.get("status") or "").lower() in STEP_FAILURE_STATUSES:
        return True
    response = payload.get("tool_response")
    if isinstance(response, dict):
        if (
            response.get("error")
            or response.get("stderr")
            or response.get("interrupted")
        ):
            return True
        if _failed_exit(
            response.get("exit_code")
            or response.get("exitCode")
            or response.get("returnCode")
        ):
            return True
        if str(response.get("status") or "").lower() in STEP_FAILURE_STATUSES:
            return True
    return False


def _failed_exit(code: Any) -> bool:
    return isinstance(code, int) and code != 0


# -- process plumbing --------------------------------------------------------


def _new_run_id(agent_name: str, session_id: str) -> str:
    """Mint a run id namespaced by agent and session; the uuid tail is the unique part."""
    return f"{agent_name}:{session_id}:{uuid.uuid4().hex}"


def _child_env() -> dict[str, str]:
    """Environment for a detached child, keeping the session's cwd off ``sys.path``.

    A child is a fresh interpreter, so the parent's ``-P`` does not reach it:
    ``sys.flags.safe_path`` is not inherited and ``PYTHONSAFEPATH`` is not set by
    the flag. Without this, a project file named after a stdlib module shadows the
    real one and the child cannot boot ``runpy``, so flush and resolve die in
    exactly the directories the wired flag protects the parent from. The variable
    is honoured from 3.11 and ignored before it, which ``-P`` is not, so it is
    safe on every interpreter this package supports.
    """
    return {**os.environ, "PYTHONSAFEPATH": "1"}


def _spawn_stderr(home: Path) -> Any:
    """Append handle for child stderr, so a child that dies leaves a trace.

    Discarding it is why this class of failure stayed invisible: the child died
    before reaching the fail-open contract in ``main``, so nothing anywhere
    recorded that it had run. Truncated past a bound, because a machine stuck in
    the broken state writes one traceback per hook event forever. Falls back to
    ``DEVNULL``: a diagnostic must never itself be the reason the loop breaks.
    """
    try:
        home.mkdir(parents=True, exist_ok=True)
        log = home / HOOK_FAILURES_LOG
        if log.exists() and log.stat().st_size > HOOK_FAILURES_LOG_MAX_BYTES:
            log.replace(log.with_suffix(log.suffix + ".1"))
        return log.open("ab")
    except OSError:
        return subprocess.DEVNULL


def _spawn_detached(*args: str) -> None:
    """Start a detached hook subprocess, insulated from the session's directory.

    ``cwd`` is the loop's own state directory rather than the editor's, so a
    project file named after a stdlib module cannot shadow it however the child
    interpreter resolves imports. ``PYTHONSAFEPATH`` says the same thing to 3.11
    and later; this says it to every version, which is what the 3.10 floor needs.
    Neither detached command reads the working directory: ``resolve`` is keyed by
    session id and ``flush`` by an absolute path.
    """
    home = hyper_home()
    stderr = _spawn_stderr(home)
    try:
        # Fixed argv from sys.executable, never a shell: not an injection surface.
        subprocess.Popen(  # nosec B603
            [sys.executable, "-m", "hyperstruck.ide.hook", *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            start_new_session=True,
            close_fds=True,
            env=_child_env(),
            cwd=str(home),
        )
    finally:
        if stderr is not subprocess.DEVNULL:
            with contextlib.suppress(OSError):
                stderr.close()


def _spawn_flush(path: str | os.PathLike[str]) -> None:
    """Spawn a detached flush process so delivery never delays the prompt."""
    try:
        _spawn_detached("flush", str(path))
    except (OSError, ValueError):
        pass


def _spawn_resolve(session_id: str) -> None:
    """Spawn a detached resolve process so recall never delays prompt submission."""
    try:
        _spawn_detached("resolve", session_id)
        _debug(f"resolve spawned: session {session_id}")
    except (OSError, ValueError) as exc:
        _debug(f"resolve spawn failed ({type(exc).__name__}): {exc}")


def _emit_injection(injected_text: str | None, args: argparse.Namespace) -> None:
    """Emit the resolved learnings for the editor to inject before the model acts."""
    if not injected_text:
        return
    if args.emit == "text":
        sys.stdout.write(injected_text)
        return
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": injected_text,
            }
        },
        sys.stdout,
    )


def _emit_tool_context(injected_text: str | None, source: str) -> bool:
    """Emit one tool-hook context payload, returning whether context was emitted."""
    if not injected_text:
        return False
    if source == SOURCE_CURSOR:
        json.dump({"additional_context": injected_text}, sys.stdout)
    else:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": injected_text,
                }
            },
            sys.stdout,
        )
    return True


def _inject_pending(session_id: str, source: str) -> None:
    """Emit detached recall exactly once, claiming it only after it validates."""
    try:
        recall = state.peek_recall(session_id)
        if recall is None or not _combined_injection(
            recall.get("injected_text"), recall.get("injected_facts_text")
        ):
            return
        active = state.read_active(session_id)
        if (
            active is None
            or active.is_injected
            or recall.get("run_id") != active.run_id
        ):
            return
        claimed = state.claim_recall(session_id)
        if claimed is None:
            return  # a parallel hook won the claim
        # Only Claude Code records what its editor accepted, so only there can a marker
        # ever be redeemed for evidence. Stamping Cursor's block would spend the
        # customer's context on an identifier nothing can read back.
        block = _combined_injection(
            claimed.get("injected_text"), claimed.get("injected_facts_text")
        )
        if not block:
            # The peek above and this claim are separate reads. Stamping an empty block
            # makes it truthy, so the marker alone would be emitted: context spent on an
            # identifier with nothing behind it, and the turn marked injected.
            return
        if source == SOURCE_CLAUDE_CODE:
            block = receipt.stamp(block, active.run_id)
        if not _emit_tool_context(block, source):
            return
        offered = tuple(str(item) for item in claimed.get("offered_learning_ids") or ())
        claims = tuple(str(item) for item in claimed.get("offered_claim_ids") or ())
        merged = tuple(dict.fromkeys((*active.offered_learning_ids, *offered)))
        merged_claims = tuple(dict.fromkeys((*active.offered_claim_ids, *claims)))
        state.write_active(
            session_id,
            replace(
                active,
                is_injected=True,
                offered_learning_ids=merged,
                offered_claim_ids=merged_claims,
            ),
            reset_steps=False,
        )
    except Exception as exc:  # noqa: BLE001 - context injection always fails open
        _debug(f"inject failed ({type(exc).__name__}): {exc}")


def resolve_session_id(
    payload: dict[str, Any], cwd: str, args: argparse.Namespace
) -> str:
    """The editor's session id from argv or the hook payload, else a stable fallback.

    The fallback (terminal session leader + repo digest) is stable across the
    three hook processes of one turn when they share a terminal and repo, so they
    still rendezvous when the editor omits a session id.
    """
    explicit = args.session or _first(
        payload, ("session_id", "conversation_id", "sessionId", "threadId", "thread_id")
    )
    if explicit:
        return str(explicit)
    try:
        sid = os.getsid(0)
    except OSError:
        sid = 0
    digest = hashlib.sha1(
        cwd.encode("utf-8", "ignore"), usedforsecurity=False
    ).hexdigest()[:12]
    return f"derived-{sid}-{digest}"


def _source(args: argparse.Namespace) -> str:
    return args.source or SOURCE_CLAUDE_CODE


def _cwd(payload: dict[str, Any], args: argparse.Namespace) -> str:
    return args.cwd or payload.get("cwd") or os.getcwd()


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    return None


def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return {"_hyper_parse_error": f"invalid JSON on stdin: {exc}"}
    return data if isinstance(data, dict) else {}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hyperstruck.ide.hook", add_help=False)
    parser.add_argument(
        "command", choices=["prompt", "tool", "stop", "resolve", "flush", "distill"]
    )
    parser.add_argument("flush_path", nargs="?", default=None)
    parser.add_argument(
        "--source", choices=[SOURCE_CLAUDE_CODE, SOURCE_CURSOR], default=None
    )
    parser.add_argument("--session", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--native-status", dest="native_status", default=None)
    parser.add_argument("--emit", choices=["json", "text"], default="json")
    parser.add_argument("--inject", action="store_true")
    parser.add_argument("--readonly", action="store_true")
    # Omitted purpose stays agent_loop. Already-installed --readonly skill
    # commands (and inject-only auto-installs that never pass a flag) must keep
    # contributing; human inspection has to pass explicit_recall.
    parser.add_argument(
        "--resolve-purpose",
        type=ResolvePurpose,
        choices=tuple(ResolvePurpose),
        default=ResolvePurpose.AGENT_LOOP,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Dispatch one hook command. Always returns 0: the loop must fail open."""
    try:
        args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 0
    try:
        load_env()  # bring ~/.hyperstruck/.env (auth + configured agent) into env
        _debug(
            f"fired command={args.command} source={args.source or SOURCE_CLAUDE_CODE}"
        )
        if args.command == "resolve":
            if args.flush_path:
                cmd_resolve(args.flush_path)
            return 0
        if args.command == "flush":
            cmd_flush(args)
            return 0
        payload = _read_stdin()
        if args.command == "prompt":
            cmd_prompt(payload, args)
        elif args.command == "tool":
            cmd_tool(payload, args)
        elif args.command == "stop":
            cmd_stop(payload, args)
        elif args.command == "distill":
            cmd_distill(payload, args)
    except (
        BaseException
    ):  # noqa: BLE001 - the loop must never break the editor, even on cancellation/interrupt
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
