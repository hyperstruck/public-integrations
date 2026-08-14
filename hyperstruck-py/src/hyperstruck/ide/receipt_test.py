from __future__ import annotations

import json
from pathlib import Path

from hyperstruck.ide import receipt

_BLOCK = "Relevant learnings:\n- Name the tenant in every query on a shared table."


def _accepted(run_id: str, *, body: str = _BLOCK) -> str:
    return json.dumps(
        {
            "type": "attachment",
            "attachment": {
                "type": "hook_additional_context",
                "hookEvent": "PostToolUse",
                "content": [f"{receipt.marker(run_id)}\n{body}"],
            },
        }
    )


def _emitted(run_id: str) -> str:
    """What the hook printed, which the editor records separately from what it took."""
    return json.dumps(
        {
            "type": "attachment",
            "attachment": {
                "type": "hook_success",
                "hookEvent": "PostToolUse",
                "stdout": json.dumps(
                    {
                        "hookSpecificOutput": {
                            "additionalContext": f"{receipt.marker(run_id)}\n{_BLOCK}"
                        }
                    }
                ),
            },
        }
    )


def _transcript(tmp_path: Path, *lines: str) -> str:
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_the_record_is_found_by_its_marker_not_by_its_position(tmp_path: Path) -> None:
    """A denied or dropped injection must not shift which run a record belongs to.

    This is the whole reason the marker exists: counting records in an append-only,
    multi-turn transcript pairs the wrong verdict with the wrong learnings the first
    time any turn fails to inject, and does it silently.
    """
    path = _transcript(
        tmp_path,
        _accepted("run-1", body="- An earlier turn's rule."),
        _emitted("run-2"),
        _accepted("run-3"),
    )

    found = receipt.acceptance_record(path, "run-3")

    assert found is not None
    assert "Name the tenant" in found
    assert "An earlier turn's rule" not in found


def test_the_hooks_own_stdout_is_not_mistaken_for_the_editors_acceptance(
    tmp_path: Path,
) -> None:
    """The emitted record carries the same text; only the editor's record is evidence."""
    path = _transcript(tmp_path, _emitted("run-1"))

    assert receipt.acceptance_record(path, "run-1") is None


def test_every_missing_or_broken_transcript_reports_nothing(tmp_path: Path) -> None:
    """Silence, uniformly: an unreadable file says nothing about what the model saw."""
    assert receipt.acceptance_record(None, "run-1") is None
    assert receipt.acceptance_record(str(tmp_path / "absent.jsonl"), "run-1") is None
    assert receipt.acceptance_record(_transcript(tmp_path, "{not json"), "run-1") is None
    assert receipt.acceptance_record(_transcript(tmp_path, _accepted("other")), "r") is None


def test_a_recall_injected_twice_reports_both_blocks(tmp_path: Path) -> None:
    """Exposure is a disjunction over a learning's offers, so both blocks count."""
    path = _transcript(
        tmp_path,
        _accepted("run-1", body="- The first block's rule."),
        _accepted("run-1", body="- The second block's rule."),
    )

    found = receipt.acceptance_record(path, "run-1")

    assert found is not None
    assert "first block" in found and "second block" in found


def test_a_sibling_hooks_context_in_the_same_record_is_not_uploaded(
    tmp_path: Path,
) -> None:
    """One record's content is a list, and the editor puts every hook's context in it.

    Joining the whole list would send another tool's output to the hosted API for no
    benefit: the matcher only ever looks for our own fragments, so a sibling entry is
    pure exfiltration of something the customer never opted in to sending.
    """
    path = _transcript(
        tmp_path,
        json.dumps(
            {
                "type": "attachment",
                "attachment": {
                    "type": "hook_additional_context",
                    "content": [
                        "SIEM alert: credentials rotated for svc-billing",
                        f"{receipt.marker('run-1')}\n{_BLOCK}",
                    ],
                },
            }
        ),
    )

    found = receipt.acceptance_record(path, "run-1")

    assert found is not None
    assert "Name the tenant" in found
    assert "svc-billing" not in found


def test_the_marker_leads_the_block_so_a_cut_tail_still_resolves() -> None:
    """Truncation must cost the rules it cut, never the whole run's evidence."""
    stamped = receipt.stamp("- A rule the editor may or may not keep.", "run-1")

    assert stamped.startswith(receipt.marker("run-1"))
    assert stamped.splitlines()[1].startswith("- A rule")


def test_an_implausibly_large_transcript_is_refused_rather_than_read(
    tmp_path, monkeypatch
) -> None:
    """The read happens on the turn's own stop hook, in the user's editing loop.

    Bounding it is what stops a pathological session file turning the learning loop into
    a visible pause, and the guard fails the same way every other failure here does: no
    receipt, so the run credits nothing rather than the editor stalling.
    """
    transcript = tmp_path / "huge.jsonl"
    transcript.write_text("x" * 4096)
    monkeypatch.setattr(receipt, "_MAX_TRANSCRIPT_BYTES", 1024)

    assert receipt.acceptance_record(str(transcript), "agent:s:r") is None

    monkeypatch.setattr(receipt, "_MAX_TRANSCRIPT_BYTES", 1024 * 1024)
    transcript.write_text(
        json.dumps(
            {
                "attachment": {
                    "type": "hook_additional_context",
                    "content": [f"{receipt.marker('agent:s:r')}\n- a rule"],
                }
            }
        )
        + "\n"
    )

    assert receipt.acceptance_record(str(transcript), "agent:s:r") is not None


def test_a_marked_record_of_an_unknown_shape_is_reported_not_swallowed(
    tmp_path, monkeypatch, capsys
) -> None:
    """The editor changing how it records an accepted hook ends the whole credit path.

    Every run would then report nothing, which the boundary reads as a corpus with
    nothing worth crediting. A silent skip here is the difference between a one-line
    diagnostic and a corpus-wide audit.
    """
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "attachment": {
                    "type": "some_new_shape",
                    "content": [f"{receipt.marker('agent:s:r')}\n- a rule"],
                }
            }
        )
        + "\n"
    )

    assert receipt.acceptance_record(str(transcript), "agent:s:r") is None
    assert "some_new_shape" in capsys.readouterr().err
