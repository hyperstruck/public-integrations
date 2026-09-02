"""The secondary net over free text: what it catches, and what it must never break.

The interface takes **spans**, because that is what every detector produces, Presidio
included. Whether a finding also reaches other occurrences of the same value is a policy
this module applies, not a shape the interface imposes, and it is the same fenced
whole-token rule the declared-value scrubber already uses.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Sequence

from hyperstruck.runtime.declarations import SECRET, SHAREABLE, USER_DATA
from hyperstruck.runtime.scanning import (
    CompositeScanner,
    Finding,
    NullScanner,
    PresidioScanner,
    scan_and_scrub,
)

EMAIL = "ada@example.com"


def _span(haystack: str, needle: str, *, label: str | None = None, kind: str = "PII") -> Finding:
    """A span finding for ``needle`` inside ``haystack``, as a real detector reports one."""
    index = haystack.find(needle)
    return Finding(start=index, end=index + len(needle), kind=kind, label=label)


class _Finds:
    """A scanner that reports occurrences of one value, by span.

    ``only_containing`` narrows it to texts carrying a marker, so a test can put the
    detector's reach in one field and prove the *echo pass* is what reached the other. A
    scanner that fired everywhere would test the fake rather than the policy.
    """

    def __init__(
        self,
        needle: str,
        label: str | None = USER_DATA,
        only_containing: str | None = None,
    ) -> None:
        self._needle = needle
        self._label = label
        self._only_containing = only_containing

    def scan(self, text: str) -> Sequence[Finding]:
        if self._only_containing is not None and self._only_containing not in text:
            return ()
        findings = []
        start = text.find(self._needle)
        while start >= 0:
            findings.append(
                Finding(
                    start=start,
                    end=start + len(self._needle),
                    kind="PII",
                    label=self._label,
                )
            )
            start = text.find(self._needle, start + 1)
        return tuple(findings)


def test_no_scanner_is_the_default_and_returns_the_payload_untouched() -> None:
    payload = {"note": EMAIL}
    result = scan_and_scrub(payload, None)
    assert result.payload is payload
    assert result.is_clean


def test_a_scanner_that_finds_nothing_changes_nothing() -> None:
    payload = {"note": "nothing here"}
    result = scan_and_scrub(payload, _Finds(EMAIL))
    assert result.payload == payload
    assert result.is_clean


def test_a_finding_is_scrubbed_out_of_the_payload_before_it_leaves_the_process() -> None:
    result = scan_and_scrub({"note": f"write to {EMAIL} today"}, _Finds(EMAIL))
    assert result.payload == {"note": f"write to [REDACTED:{USER_DATA}] today"}
    assert not result.is_clean
    assert "1" in result.describe()


def test_the_same_datum_echoed_into_another_field_is_scrubbed_too() -> None:
    """The case a scanner is fitted for: an agent copying a value out of one result.

    The detector reports where it looked; whether the same datum elsewhere is also
    sensitive is this module's policy, and it is the same rule the declared-value scrubber
    applies.
    """
    payload = {"result": f"contact {EMAIL}", "summary": f"emailed {EMAIL} about it"}
    result = scan_and_scrub(payload, _Finds(EMAIL))
    assert EMAIL not in str(result.payload)
    assert result.payload["summary"] == f"emailed [REDACTED:{USER_DATA}] about it"


def test_the_echo_pass_is_fenced_so_a_coincidental_substring_survives() -> None:
    """The same fence, and the same reason, as the declared-value scrubber's."""
    payload = {"result": "code 1234 here", "other": "order-12345 shipped"}
    result = scan_and_scrub(payload, _Finds("1234", only_containing="code"))
    assert result.payload["result"] == f"code [REDACTED:{USER_DATA}] here"
    assert result.payload["other"] == "order-12345 shipped"


def test_a_span_shorter_than_the_floor_is_scrubbed_but_never_echoed() -> None:
    """A one or two character finding scrubbed across a payload corrupts unrelated content."""
    payload = {"result": "pick 7 now", "other": "7 of 77"}
    result = scan_and_scrub(payload, _Finds("7", only_containing="pick"))
    assert result.payload["other"] == "7 of 77"


def test_overlapping_spans_merge_rather_than_being_replaced_twice() -> None:
    class _Overlapping:
        def scan(self, text: str) -> Sequence[Finding]:  # noqa: ARG002
            return (
                Finding(start=0, end=5, kind="A", label=SHAREABLE),
                Finding(start=3, end=8, kind="B", label=USER_DATA),
            )

    result = scan_and_scrub("0123456789", _Overlapping())
    # One marker, and the stricter of the two labels: the join is escalate-only here too.
    assert result.payload == f"[REDACTED:{USER_DATA}]89"


def test_an_impossible_span_is_ignored_rather_than_corrupting_the_text() -> None:
    class _Bad:
        def scan(self, text: str) -> Sequence[Finding]:  # noqa: ARG002
            return (
                Finding(start=5, end=2, kind="X"),
                Finding(start=0, end=99, kind="X"),
                Finding(start=-1, end=3, kind="X"),
            )

    assert scan_and_scrub("hello", _Bad()).payload == "hello"


def test_a_finding_with_no_label_reads_as_the_most_restrictive_member() -> None:
    """A detector that says what it found without saying how sensitive has licensed nothing."""
    result = scan_and_scrub({"note": f"see {EMAIL}"}, _Finds(EMAIL, label=None))
    assert result.payload == {"note": f"see [REDACTED:{SECRET}]"}


def test_two_scanners_disagreeing_about_one_span_resolve_to_the_stricter_label() -> None:
    composite = CompositeScanner([_Finds(EMAIL, label=SHAREABLE), _Finds(EMAIL, label=SECRET)])
    result = scan_and_scrub({"note": f"see {EMAIL}"}, composite)
    assert result.payload == {"note": f"see [REDACTED:{SECRET}]"}


def test_a_scanner_that_raises_is_dropped_rather_than_taking_the_run_with_it() -> None:
    class _Raises:
        def scan(self, text: str) -> Sequence[Finding]:  # noqa: ARG002
            raise RuntimeError("model not loaded")

    composite = CompositeScanner([_Raises(), _Finds(EMAIL)])
    result = scan_and_scrub({"note": f"see {EMAIL}"}, composite)
    assert result.payload == {"note": f"see [REDACTED:{USER_DATA}]"}


def test_the_null_scanner_is_the_default_and_finds_nothing() -> None:
    assert scan_and_scrub({"note": EMAIL}, NullScanner()).is_clean


def test_the_presidio_adapter_hands_its_offsets_straight_through() -> None:
    """It used to slice the text down to a value, discarding the one thing Presidio was
    most sure of and making "this occurrence and not that one" inexpressible."""
    text = f"write to {EMAIL} today"
    start = text.find(EMAIL)

    class _Analyzer:
        def analyze(self, *, text: str, language: str) -> Any:  # noqa: ARG002
            return [
                SimpleNamespace(start=start, end=start + len(EMAIL), entity_type="EMAIL_ADDRESS")
            ]

    scanner = PresidioScanner(analyzer=_Analyzer())
    finding = scanner.scan(text)[0]
    assert (finding.start, finding.end) == (start, start + len(EMAIL))
    assert finding.kind == "EMAIL_ADDRESS"
    # Coarse by design: the analyser says what it found, not how restricted it is, and
    # user_data is the honest reading of a personal-data detector's output.
    assert finding.label == USER_DATA


def test_a_presidio_analyzer_that_raises_scrubs_nothing_and_does_not_propagate() -> None:
    class _Analyzer:
        def analyze(self, *, text: str, language: str) -> Any:  # noqa: ARG002
            raise RuntimeError("spacy model missing")

    assert PresidioScanner(analyzer=_Analyzer()).scan("anything") == ()
