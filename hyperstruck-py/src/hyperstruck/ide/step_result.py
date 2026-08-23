"""What a finished tool step reports about its outcome, beyond pass or fail.

A step used to ship its name, its path or command, and a status. Extraction can ground a
transferable rule only when the trace carries a specific it can point at, and a name with no
outcome rarely does, so the corpus barely grew: over fifteen production days, 1.7% of
observed runs produced a learning, and none of 21,401 offered rules carried a gate predicate.

What ships is the *shape* of a failure, under the name the server derives a gate from. Raw
tool output is source and never leaves the machine; a status of "failed" is true of every
failure and so tells a later run nothing. A masked failure shape says *which* failure, which
is the only thing here a rule can usefully fire on. See :mod:`failure_template`.

**An exit status was the original design and the measurement retired it.** Claude Code puts
one nowhere a hook can read (0 of 35,981 real tool results carry one under any name), and
where one does exist it barely discriminates: of 1,181 real failures carrying an exit status,
86.3% were ``1``. A gate on ``error_code='1'`` fires on any generic failure, which is the
degenerate gate this module was written to avoid, reached by a different route.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hyperstruck.contracts import published_names
from hyperstruck.ide.failure_template import failure_signature
from hyperstruck.ide.host_vocabularies import failure_framing
from hyperstruck.redaction import scrub_secrets

# The field name the server derives a gate from for a failed step. Sending any other name
# yields no gate and no error, so the published contract is vendored beside this file and a
# test holds the two together.
GATE_FIELD = "error_type"

_CONTRACT = Path(__file__).parent / "gate_published_fields.json"


def published_fields() -> frozenset[str]:
    """The field names the server derives a gate from, as published by it."""
    return published_names(_CONTRACT, "fields")


def gate_bearing_result(
    payload: dict[str, Any], *, is_error: bool, source: str = ""
) -> dict[str, Any] | None:
    """The outcome fields this step may report, or None when it has none worth reporting.

    A successful step reports nothing: a gate exists to recognise a dead end, and there is
    no dead end to recognise. A failure reports what it called itself, and nothing else.
    """
    if not is_error or not is_operand_admitted_on_support():
        return None
    text, is_host_labelled = _failure_text(payload)
    signature = failure_signature(
        text, failure_framing(source), is_host_labelled=is_host_labelled
    )
    if signature is None:
        return None
    # Scrubbing runs after validation, and a value it changes at all is dropped rather than
    # shipped: a failure's name does not contain a credential, so one that did was never the
    # name, and sending it redacted would be a quasi-identifier with a mask on. Validating
    # after scrubbing instead let a masked value through that no longer matched the shape it
    # had been validated against, which the boundary then refused silently.
    scrubbed = scrub_secrets(signature)
    if scrubbed != signature:
        return None
    return {GATE_FIELD: scrubbed}


def is_operand_admitted_on_support() -> bool:
    """Whether the boundary admits an operand on how often it has been seen across the corpus.

    The contract file has said all along that shape-derived operands are withheld until this
    is true, and nothing read it: the client shipped them anyway. That gap mattered, because
    "leaks nothing by construction" turned out to be a claim about a masking rule rather than
    a property, and 72.7% of these operands are singletons, which are quasi-identifiers and
    dead gates at once. Withholding is the same discipline the decline reasons and the recall
    outcomes already follow, applied to the one field that has a privacy argument attached.
    """
    if GATE_FIELD not in published_fields():
        # The contract is consulted at runtime rather than only by a test. A field name that
        # drifts from what the boundary publishes yields no gate and no error anywhere, which
        # is exactly the silent drift vendoring the contract exists to prevent.
        return False
    return "operand_support_floor_enforced" in published_names(
        _CONTRACT, "enforced_guarantees"
    )


def _failure_text(payload: dict[str, Any]) -> tuple[str, bool]:
    """This step's account of how it failed, and whether the host labelled it as one.

    Claude Code delivers a failed call's whole result as a plain string, which is not
    labelled: it is whatever the tool produced, and only the host's own framing inside it
    says that it is an error. Cursor puts the message in ``stderr`` or ``error``, which are
    fields that mean "this is the error" and need no framing.

    The distinction decides whether an operand may be derived at all, because the string
    case is also how a tool's *output* would arrive.

    The first field that carries anything wins, rather than all of them joined. Each of
    these fields separately means "this is the error", but their concatenation means only
    "here is everything", and the operand would then be read from the tail of whichever
    field happened to come last instead of from the one naming the failure.
    """
    response = payload.get("tool_response")
    if response is None:
        response = payload.get("tool_result")
    labelled = [payload.get("error"), payload.get("stderr")]
    if isinstance(response, dict):
        labelled += [response.get("error"), response.get("stderr")]
    for part in labelled:
        if part:
            return str(part), True
    return (response if isinstance(response, str) else ""), False
