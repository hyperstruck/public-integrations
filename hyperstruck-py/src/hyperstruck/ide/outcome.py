"""Resolve a turn's terminal outcome from evidence the turn itself produced.

A transient failure on the way to a fix is normal in coding, so a turn is scored
on where it ended, not on whether any step failed. The label is decided at the
turn's own stop, from objective or behavioural signals only, with no language
heuristics:

1. the execution oracle, the trailing test/command result;
2. the host's native terminal status, against the vocabulary that host declared;
3. the objective evidence a turn's own acts carry (below).

A turn none of them speaks for is *unevidenced*, which is its own answer rather
than a guess: it closes the loop and credits nothing. Crediting it instead would
be a fabrication, and the only reason the old design needed the successor turn
was to retract the fabrications it produced.

Tier 2 exists because a turn made of acts other than shell commands had no
evidence at all, and so was declined however much it did. That is most non-coding
agent work: browser automation, API calls, messaging.

It reads exactly one signal, because only one is unambiguous without a shell's
verdict: something material failed, and something material afterwards worked. That
sequence cannot happen by accident, and it is the turn class most worth learning
from. Everything else stays unevidenced on purpose. A trailing act that succeeded
is a fact about the call rather than about the work, and a trailing act that failed
is indistinguishable from a turn the user interrupted mid-step, which is precisely
the fabrication the ladder abstains to avoid.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from hyperstruck.ide.constants import (
    MATERIAL_KINDS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STEP_KIND_COMMAND,
)


class TurnOutcome(StrEnum):
    """What the turn's own evidence supports, or that it supports nothing."""

    SUCCESS = "success"
    FAILURE = "failure"
    UNEVIDENCED = "unevidenced"

    @property
    def is_evidenced(self) -> bool:
        return self is not TurnOutcome.UNEVIDENCED

    @property
    def is_success(self) -> bool:
        return self is TurnOutcome.SUCCESS


class NativeStatusVocabulary:
    """One host's terminal statuses, as that host defines them.

    Held as data rather than branched on, so the outcome path never names a
    source. A host that declares nothing abstains on every status instead of
    inheriting another host's meanings, which is the safe direction: an
    unrecognised status becomes no evidence rather than a silent success.
    """

    __slots__ = ("failure", "success")

    def __init__(self, *, success: frozenset[str], failure: frozenset[str]) -> None:
        self.success = success
        self.failure = failure

    def classify(self, native_status: str) -> TurnOutcome:
        normalised = native_status.strip().lower()
        if normalised in self.failure:
            return TurnOutcome.FAILURE
        if normalised in self.success:
            return TurnOutcome.SUCCESS
        return TurnOutcome.UNEVIDENCED


EMPTY_VOCABULARY = NativeStatusVocabulary(success=frozenset(), failure=frozenset())


def provisional_outcome(
    steps: list[dict[str, Any]],
    native_status: str | None = None,
    vocabulary: NativeStatusVocabulary = EMPTY_VOCABULARY,
) -> TurnOutcome:
    """The turn's label, from the execution oracle, then its acts, then the host."""
    last_command = _last_command_status(steps)
    if last_command is not None:
        return (
            TurnOutcome.SUCCESS
            if last_command == STATUS_COMPLETED
            else TurnOutcome.FAILURE
        )
    # The host's own verdict outranks anything inferred from the steps. It is a first-party
    # statement and a recovery is a second-party inference, so a turn the host reports as
    # cancelled must not be credited because something failed and something later worked
    # before the user pressed Escape.
    if native_status:
        declared = vocabulary.classify(native_status)
        if declared is not TurnOutcome.UNEVIDENCED:
            return declared
    return _evidence_from_acts(steps)


def _evidence_from_acts(steps: list[dict[str, Any]]) -> TurnOutcome:
    """What a turn's material acts objectively show, where they show anything.

    One signal only: a recovery. Something material failed and something material
    afterwards worked, which cannot happen by accident and says the turn got somewhere.

    A trailing act that merely succeeded is not added, because it is a fact about the call
    and not about the work. A trailing act that merely failed is not added either, because
    it is indistinguishable from a turn the user interrupted mid-step, and an orphan
    recovered by the sweep is exactly that case.
    """
    material = [step for step in steps if step.get("kind") in MATERIAL_KINDS]
    if _recovered(material):
        return TurnOutcome.SUCCESS
    return TurnOutcome.UNEVIDENCED


def _terminal_failure(material: list[dict[str, Any]]) -> bool:
    return bool(material) and material[-1].get("status") == STATUS_FAILED


def _recovered(material: list[dict[str, Any]]) -> bool:
    """A failed material step followed by a later one that worked."""
    if _terminal_failure(material):
        # A recovery followed by a further failure is exactly as indistinguishable from an
        # interruption as a bare trailing failure is, and reading only the first fail-success
        # pair credited it. The recovery has to be where the turn actually ended.
        return False
    seen_failure = False
    for step in material:
        if step.get("status") == STATUS_FAILED:
            seen_failure = True
        elif seen_failure and step.get("status") == STATUS_COMPLETED:
            return True
    return False


def _last_command_status(steps: list[dict[str, Any]]) -> str | None:
    """The status of the last command/test step, or ``None`` if the turn ran none."""
    for step in reversed(steps):
        if step.get("kind") == STEP_KIND_COMMAND:
            return step.get("status")
    return None
