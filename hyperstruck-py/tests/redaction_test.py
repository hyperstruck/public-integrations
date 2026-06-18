"""Client-side redaction: declared-field strip plus known-value scrub."""

from __future__ import annotations

from hyperstruck.redaction import REDACTION_MARKER, redact_episode_payload


def _payload_with_secret() -> dict:
    return {
        "run_id": "bot:1",
        "goal": "look up the customer",
        "steps": [
            {
                "id": "c1",
                "name": "lookup_ssn",
                "args": {"ssn": "123-45-6789", "name": "Ada"},
                "status": "completed",
                "result": "found record for SSN 123-45-6789",
                "error": None,
                "declared_sensitivity": {"args": {"ssn": "pii"}},
            },
            {
                "id": "c2",
                "name": "summarise",
                "args": {"note": "the ssn was 123-45-6789"},
                "status": "completed",
                "result": "ok",
                "error": None,
                "declared_sensitivity": None,
            },
        ],
        "outcome": {"is_success": True, "total_steps": 2, "completed_steps": 2, "failed_steps": 0},
        "source_framework": "langgraph",
        "thread_id": None,
    }


def test_declared_field_is_stripped() -> None:
    redacted = redact_episode_payload(_payload_with_secret())
    assert redacted["steps"][0]["args"]["ssn"] == "[REDACTED:pii]"


def test_undeclared_field_preserved() -> None:
    redacted = redact_episode_payload(_payload_with_secret())
    assert redacted["steps"][0]["args"]["name"] == "Ada"


def test_known_value_scrubbed_from_result_and_echo() -> None:
    redacted = redact_episode_payload(_payload_with_secret())
    # The literal secret is scrubbed from the tool result...
    assert "123-45-6789" not in redacted["steps"][0]["result"]
    assert REDACTION_MARKER in redacted["steps"][0]["result"]
    # ...and from a later step that echoed it in an undeclared field.
    assert "123-45-6789" not in redacted["steps"][1]["args"]["note"]


def test_input_not_mutated() -> None:
    original = _payload_with_secret()
    redact_episode_payload(original)
    assert original["steps"][0]["args"]["ssn"] == "123-45-6789"
    assert original["steps"][1]["args"]["note"] == "the ssn was 123-45-6789"


def test_no_declared_fields_leaves_values() -> None:
    payload = _payload_with_secret()
    for step in payload["steps"]:
        step["declared_sensitivity"] = None
    redacted = redact_episode_payload(payload)
    assert redacted["steps"][0]["args"]["ssn"] == "123-45-6789"
