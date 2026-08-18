"""Resolve a turn's terminal outcome from evidence the turn itself produced.

A transient failure on the way to a fix is normal in coding, so a turn is scored
on where it ended, not on whether any step failed. The label is decided at the
turn's own stop, from objective or behavioural signals only, with no language
heuristics:

1. the execution oracle, the trailing test/command result;
2. the host's native terminal status, against the vocabulary that host declared.

There is no third tier. A turn neither signal speaks for is *unevidenced*, which
is its own answer rather than a guess: it closes the loop and credits nothing.
Crediting it instead would be a fabrication, and the only reason the old design
needed the successor turn was to retract the fabrications it produced.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from hyperstruck.ide.constants import STATUS_COMPLETED, STEP_KIND_COMMAND


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
    """The turn's label, from the execution oracle then the host's own status."""
    last_command = _last_command_status(steps)
    if last_command is not None:
        return (
            TurnOutcome.SUCCESS
            if last_command == STATUS_COMPLETED
            else TurnOutcome.FAILURE
        )
    if native_status:
        return vocabulary.classify(native_status)
    return TurnOutcome.UNEVIDENCED


def _last_command_status(steps: list[dict[str, Any]]) -> str | None:
    """The status of the last command/test step, or ``None`` if the turn ran none."""
    for step in reversed(steps):
        if step.get("kind") == STEP_KIND_COMMAND:
            return step.get("status")
    return None
