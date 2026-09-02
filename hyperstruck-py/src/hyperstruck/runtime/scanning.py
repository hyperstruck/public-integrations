"""Content scanning: the secondary net, off by default, and an honest asymmetry.

Origin labelling is the primary mechanism and it is exact where it applies: a tool is
declared once and everything flowing out of it inherits the label. Free text is where it
under-delivers. A tool returning a meeting transcript has one label and arbitrary content
inside it, and that is a real customer path rather than a hypothetical one.

So scanning is an **interface**, not a bundled dependency, and it is off until a customer
turns it on. Presidio is the mature free option and is Python-first, so a documented
adapter for it ships here. The credible Node equivalents are materially thinner (pii-scan
describes itself as development-grade, Grepture is a hosted gateway rather than a library,
and GLiNER-class zero-shot detectors need a model runtime in process), so the TypeScript
seat gets a customer-supplied hook instead of an adapter. The two seats are not symmetric
here and this says so rather than pretending.

**When the two signals disagree, escalate only.** A scan may raise a value's sensitivity
above what its tool declared and may never lower it. That is the same lattice join the
origin propagation already uses, so the two compose rather than compete, and it fails in
the safe direction. A tool declared permissively whose output turns out to carry personal
data is the case the net exists for. A tool declared restrictively whose content looks
innocuous is not evidence that the declaration was wrong.

**What a scan does here is redact, not relabel.** ``declared_sensitivity`` carries argument
labels, and a finding in a tool's *result* has nowhere to go in that field: labelling the
step would say the wrong thing about its arguments and would still send the result. So a
finding is scrubbed out of the payload before it leaves the process, over the same safe
traversal the declared-value redaction already uses, and the run reports how many spans
went. A scanner that finds nothing changes nothing.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import re

from hyperstruck.redaction import scrub_strings
from hyperstruck.runtime.declarations import UNDECLARED_SENSITIVITY, USER_DATA
from hyperstruck.runtime.declarations import join as join_labels



def _labelled_marker(label: str | None) -> str:
    """The marker a scrubbed span is replaced with, naming how restricted it was.

    An absent label reads as the most restrictive member rather than as unlabelled: a
    detector that says what it found without saying how sensitive it is has not licensed
    anything weaker.
    """
    return f"[REDACTED:{label or UNDECLARED_SENSITIVITY}]"


logger = logging.getLogger(__name__)

# Below this, a detected span is not scrubbed. A one or two character "finding" scrubbed
# across a whole payload corrupts unrelated content, which is the same bound and the same
# reason the declared-value scrubber applies one.
MIN_SCAN_LENGTH = 3


@dataclass(frozen=True)
class Finding:
    """One span a scanner believes is sensitive, and how sensitive it thinks it is.

    **Spans, not values, and the reason is that every detector produces spans.** Presidio's
    ``RecognizerResult`` is ``(entity_type, start, end, score)``, and so is the output of
    any regex or model-based detector worth fitting. An earlier version of this interface
    took a value, which forced the adapter to slice the text down and throw the offsets
    away: a lossy conversion this package chose rather than one the detector imposed, and
    it made "this occurrence is sensitive and that one is not" inexpressible.

    Whether a finding also reaches *other* occurrences of the same value is a separate
    decision and is not the interface's to make. See :func:`scan_and_scrub`.
    """

    start: int
    end: int
    kind: str = "unknown"
    # How sensitive, on the boundary's own lattice. Optional, because a detector says what
    # it found and not always how restricted it is; absent, the most restrictive member is
    # assumed, which is the direction the undeclared-argument default takes and for the
    # same reason.
    label: str | None = None


@runtime_checkable
class ContentScanner(Protocol):
    """What a customer plugs in. One method, so a hand-rolled scanner is three lines."""

    def scan(self, text: str) -> Sequence[Finding]:
        """Every span in ``text`` this scanner believes is sensitive."""
        ...


class NullScanner:
    """The default. Finds nothing, changes nothing, costs nothing."""

    def scan(self, text: str) -> Sequence[Finding]:  # noqa: ARG002
        return ()


class PresidioScanner:
    """The documented Python adapter, behind a guarded import.

    Presidio is not a dependency of this package and never becomes one: the analyzer pulls
    spaCy and a language model, which is a reasonable thing for a customer to opt into and
    an unreasonable thing to put in the install path of a thin client. So the import is one
    constructor wide, and its absence is an error at construction rather than a surprise on
    the first run that happens to carry a transcript.

    Every finding maps to ``user_data`` rather than to a per-entity-type lattice. Presidio's
    entity taxonomy is about what a span *is*, and the label is about what may be done with
    it, and mapping the first onto the second finely would be inventing a policy the
    customer did not state. Credentials are already covered, more precisely, by the
    existing secret detector in ``redaction.py``, so nothing is lost by keeping this coarse.
    """

    def __init__(self, *, language: str = "en", analyzer: Any = None) -> None:
        if analyzer is None:
            try:
                from presidio_analyzer import AnalyzerEngine
            except ImportError as exc:  # pragma: no cover - depends on the environment
                raise ImportError(
                    "PresidioScanner needs presidio-analyzer, which Hyperstruck does not "
                    "install: `pip install presidio-analyzer` and download a spaCy model. "
                    "Content scanning is opt-in precisely so this is your choice."
                ) from exc
            analyzer = AnalyzerEngine()
        self._analyzer = analyzer
        self._language = language

    def scan(self, text: str) -> Sequence[Finding]:
        try:
            results = self._analyzer.analyze(text=text, language=self._language)
        except Exception as exc:  # noqa: BLE001 - a scanner fault must not break the run
            logger.warning("Hyperstruck content scan failed, nothing scrubbed: %s", exc)
            return ()
        # Presidio's offsets are handed straight through. The adapter used to slice them
        # down to a value, which threw away the one thing the detector was most sure of.
        findings = []
        for result in results:
            start = int(getattr(result, "start", -1))
            end = int(getattr(result, "end", -1))
            if 0 <= start < end <= len(text) and end - start >= MIN_SCAN_LENGTH:
                findings.append(
                    Finding(
                        start=start,
                        end=end,
                        kind=str(getattr(result, "entity_type", "unknown")),
                        label=USER_DATA,
                    )
                )
        return tuple(findings)


class CompositeScanner:
    """Several scanners as one, joining their verdicts the only way that is safe.

    Two scanners disagreeing about one span resolves to the more restrictive label, which
    is the same join used everywhere else here. A scanner that raises is dropped for that
    call rather than taking the run with it: a secondary net is not a thing worth failing a
    customer's run over.
    """

    def __init__(self, scanners: Iterable[ContentScanner]) -> None:
        self._scanners = tuple(scanners)

    def scan(self, text: str) -> Sequence[Finding]:
        by_span: dict[tuple[int, int], Finding] = {}
        for scanner in self._scanners:
            try:
                found = scanner.scan(text)
            except Exception as exc:  # noqa: BLE001 - a secondary net, never the run
                logger.warning("Hyperstruck content scanner raised, skipping it: %s", exc)
                continue
            for finding in found:
                key = (finding.start, finding.end)
                existing = by_span.get(key)
                if existing is None:
                    by_span[key] = finding
                    continue
                joined = join_labels(existing.label, finding.label)
                if joined != existing.label:
                    by_span[key] = Finding(
                        start=finding.start,
                        end=finding.end,
                        kind=finding.kind,
                        label=joined,
                    )
        return tuple(by_span.values())


@dataclass(frozen=True)
class ScanResult:
    """What a scan did to one payload, and enough to say so in the run report."""

    payload: Any
    findings: tuple[Finding, ...]

    @property
    def is_clean(self) -> bool:
        return not self.findings

    def describe(self) -> str:
        kinds = sorted({finding.kind for finding in self.findings})
        return f"{len(self.findings)} span(s) scrubbed by content scan ({', '.join(kinds)})"


def _merge(spans: list[Finding]) -> list[Finding]:
    """Overlapping spans become one, so no span is replaced twice."""
    merged: list[Finding] = []
    for finding in sorted(spans, key=lambda f: (f.start, f.end)):
        if merged and finding.start < merged[-1].end:
            last = merged[-1]
            merged[-1] = Finding(
                start=last.start,
                end=max(last.end, finding.end),
                kind=last.kind,
                label=join_labels(last.label, finding.label),
            )
            continue
        merged.append(finding)
    return merged


def scan_and_scrub(payload: Any, scanner: ContentScanner | None) -> ScanResult:
    """Scan every string in a payload and replace what was found, in one pass.

    The traversal is the package's existing safe one rather than a second implementation,
    so an arbitrarily deep payload cannot raise a ``RecursionError`` into the host's run and
    tuples serialise the same way they already do.
    """
    if scanner is None:
        return ScanResult(payload=payload, findings=())
    # What this covers, said plainly because the boundary is narrower than "content
    # scanning" suggests: the seat passes a step's *result* and nothing else. Arguments are
    # covered by the declared-value redaction, which is exact; errors and the goal are
    # covered by neither and reach the platform's own server-side floor. A customer who
    # needs a scanner over those declares the argument carrying them instead.

    found: list[Finding] = []
    # What each detected span *said*, so the echo pass below knows what to look for and
    # under which label. Keyed by the value, because that is what an echo is.
    echoes: dict[str, Finding] = {}

    def replace_spans(text: str) -> str:
        spans = [
            finding
            for finding in scanner.scan(text)
            if isinstance(finding.start, int)
            and isinstance(finding.end, int)
            and 0 <= finding.start < finding.end <= len(text)
        ]
        if not spans:
            return text
        out = text
        for finding in reversed(_merge(spans)):
            value = text[finding.start : finding.end]
            if len(value) >= MIN_SCAN_LENGTH:
                echoes.setdefault(value, finding)
            found.append(finding)
            out = out[: finding.start] + _labelled_marker(finding.label) + out[finding.end :]
        return out

    scrubbed = scrub_strings(payload, replace_spans)
    if not found:
        return ScanResult(payload=payload, findings=())

    # **The echo pass, and why it lives here rather than in the interface.** A detector
    # reports where it looked; whether the same datum appearing in a *different* field is
    # also sensitive is a policy about this payload, and one this package has already
    # argued and tested a module away. ``redaction.py`` scrubs a declared value across the
    # whole payload fenced by non-word lookarounds and above a minimum length, precisely so
    # a short or common value cannot corrupt unrelated content. The same rule applies for
    # the same reason: a personal datum a tool returned in one field and the agent copied
    # into another is the case a scanner is fitted for, and a coincidental substring is the
    # case the fence exists for.
    if echoes:
        alternation = "|".join(
            re.escape(value) for value in sorted(echoes, key=len, reverse=True)
        )
        pattern = re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")

        def replace_echoes(text: str) -> str:
            return pattern.sub(
                lambda match: _labelled_marker(echoes[match.group(0)].label), text
            )

        scrubbed = scrub_strings(scrubbed, replace_echoes)

    return ScanResult(payload=scrubbed, findings=tuple(found))
