"""What a finished tool step reports about its outcome, beyond pass or fail.

A step used to ship its name, its path or command, and a status. Extraction can ground a
transferable rule only when the trace carries a specific it can point at, and a name with no
outcome rarely does, so the corpus barely grew: over fifteen production days, 1.7% of
observed runs produced a learning, and none of 21,401 offered rules carried a gate predicate.

What was meant to ship is the *shape* of a failure, under the name the server derives a
gate from. Raw tool output is source and never leaves the machine; a status of "failed" is
true of every failure and so tells a later run nothing. A masked failure shape says *which*
failure, which is the only thing here a rule can usefully fire on.

**A shape ships only under a provenance tier.** Every earlier route read an identifier off a
line nobody had established the host or a language runtime wrote, and each returned a
hostname, a username and an environment variable name for ordinary input. What ships now is
read under a grammar that names the author first: the host's own protocol message, or a
language runtime's error name. Anything else abstains. See
:mod:`failure_template` for the tiers, and :mod:`language_anchors` for the grammars that
license one. **Withdrawing a tier means removing its grammar there**, which is where the
policy actually lives: a separate boolean gate over the matched tier was tried and was a
tautology, because a tier that matches nothing produces no candidate to refuse.

**An exit status was the original design and the measurement retired it.** Claude Code puts
one nowhere a hook can read (0 of 35,981 real tool results carry one under any name), and
where one does exist it barely discriminates: of 1,181 real failures carrying an exit status,
86.3% were ``1``. A gate on ``error_code='1'`` fires on any generic failure, which is the
degenerate gate this module was written to avoid, reached by a different route.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from hyperstruck.contracts import published_names, published_shape
from hyperstruck.ide.debug import debug
from hyperstruck.ide.failure_template import ProvenanceTier, failure_signature
from hyperstruck.ide.host_vocabularies import host_authored_framing
from hyperstruck.redaction import scrub_secrets

# The field name the server derives a gate from for a failed step. Sending any other name
# yields no gate and no error, so the published contract is vendored beside this file and a
# test holds the two together.
GATE_FIELD = "error_type"

_CONTRACT = Path(__file__).parent / "gate_published_fields.json"


def published_fields() -> frozenset[str]:
    """The field names the server derives a gate from, as published by it."""
    return published_names(_CONTRACT, "fields")


def published_operand_shape() -> Mapping[str, object]:
    """The bounds the server validates an operand against, as published by it.

    Read rather than reimplemented, because a bound written twice moves once: the masking
    this feeds is only deterministic across machines while both ends agree on it exactly.
    """
    return published_shape(_CONTRACT, "operand_shape")


def _why_nothing_survived(tier: ProvenanceTier, source: str) -> str:
    """The abstention, named as precisely as the tier actually allows.

    The two licensed tiers do not refuse for the same reasons, so one message for both is
    wrong for one of them. The language tier hands its name straight to the published
    bounds, so a refusal there is the contract's. The host tier masks first, under a rule
    deliberately tighter than the boundary's, and that rule discards a message whose every
    word it masked or which is left too short to be a name; calling that a published bound
    would misreport the client's own choice as the boundary's, which is the same class of
    mislabel this function exists to prevent.
    """
    if tier is ProvenanceTier.UNLICENSED:
        return f"tool: no provenance tier licensed this failure (source={source!r})"
    if tier is ProvenanceTier.LANGUAGE_RUNTIME:
        return (
            "tool: gate operand refused by the published bounds, licensed by "
            f"{tier.value}"
        )
    return (
        "tool: gate operand did not survive this client's masking or the published "
        f"bounds, licensed by {tier.value}"
    )


def gate_bearing_result(
    payload: dict[str, Any], *, is_error: bool, source: str = ""
) -> dict[str, Any] | None:
    """The outcome fields this step may report, or None when it has none worth reporting.

    A successful step reports nothing: a gate exists to recognise a dead end, and there is
    no dead end to recognise. A failure reports what it called itself, and nothing else.

    **What may be read is decided by who wrote it**, in :mod:`failure_template`, and the
    decision to emit what was found is made here. Keeping the two apart is what stopped the
    previous rule leaking: the mechanism can be widened to a new frame or a new language
    without that widening silently becoming a licence to send.

    Each way of yielding nothing says so on the debug channel, and says which one it was.
    They look identical from outside and mean opposite things: no tier licensing the result
    is the common case and is by design, a bound refusing a licensed value is the tier
    working and the contract disagreeing, and the guarantee being unpublished is the whole
    lane being off. This function is the only place that holds the tier alongside the
    verdict, so a caller that tried to tell them apart could only guess, and did.
    """
    if not is_error:
        return None
    # Before extracting, not after: this is a cached read and extraction is a scan plus a
    # regex pass, so asking the cheap question first keeps the whole tier off the path
    # whenever the boundary has not promised to refuse singletons.
    if not is_operand_admitted_on_support():
        debug(
            "tool: gate operand withheld, the boundary publishes no support-floor guarantee"
        )
        return None
    tier, signature = failure_signature(
        _failure_text(payload),
        host_authored_framing(source),
        shape=published_operand_shape(),
    )
    if signature is None:
        debug(_why_nothing_survived(tier, source))
        return None
    # Scrubbing runs after validation, and a value it changes at all is dropped rather than
    # shipped: a failure's name does not contain a credential, so one that did was never the
    # name, and sending it redacted would be a quasi-identifier with a mask on. Validating
    # after scrubbing instead let a masked value through that no longer matched the shape it
    # had been validated against, which the boundary then refused silently.
    scrubbed = scrub_secrets(signature)
    if scrubbed != signature:
        debug("tool: gate operand dropped, the scrubber changed a licensed value")
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


def _failure_text(payload: dict[str, Any]) -> str:
    """This step's account of how it failed.

    Claude Code delivers a failed call's whole result as a plain string, which is not
    labelled: it is whatever the tool produced, and only the host's own framing inside it
    says that it is an error. Cursor puts the message in ``stderr`` or ``error``, which are
    fields that mean "this is the error".

    **The field name no longer decides anything about what may be read**, because it never
    could. ``stderr`` is a claim about the field, not about each line inside it: on a host
    that runs shell commands it carries progress chatter, warnings and, for something like
    ``cat /etc/passwd``, the file. Reading a line out of it because the field was named
    ``stderr`` shipped a username, an internal hostname and an environment variable name in
    testing. A labelled field is now simply text like any other, and reaches a tier only if
    a language grammar recognises what is in it.

    The first field that carries anything wins, rather than all of them joined. Each of
    these fields separately means "this is the error", but their concatenation means only
    "here is everything".
    """
    response = payload.get("tool_response")
    if response is None:
        response = payload.get("tool_result")
    labelled = [payload.get("error"), payload.get("stderr")]
    if isinstance(response, dict):
        labelled += [response.get("error"), response.get("stderr")]
    for part in labelled:
        if part:
            return str(part)
    return response if isinstance(response, str) else ""
