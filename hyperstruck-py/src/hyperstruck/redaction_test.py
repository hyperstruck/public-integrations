"""Client-side redaction: declared-field strip plus known-value scrub."""

from __future__ import annotations

from hyperstruck.redaction import (
    MIN_SCRUB_LENGTH,
    REDACTION_MARKER,
    redact_episode_payload,
)


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


def _payload_with_short_secret(value: str) -> dict:
    return {
        "run_id": "bot:1",
        "goal": "compute a total",
        "steps": [
            {
                "id": "c1",
                "name": "set_quantity",
                "args": {"qty": value},
                "status": "completed",
                "result": f"order total is 1{value}0 dollars",
                "error": None,
                "declared_sensitivity": {"args": {"qty": "secret"}},
            },
        ],
        "outcome": {"is_success": True, "total_steps": 1, "completed_steps": 1, "failed_steps": 0},
        "source_framework": "langgraph",
        "thread_id": None,
    }


def test_short_secret_below_floor_is_stripped_but_not_scrubbed() -> None:
    # A one-character declared value is still stripped from its own argument, but
    # is not scrubbed across the payload (it would corrupt unrelated content).
    assert MIN_SCRUB_LENGTH == 2
    redacted = redact_episode_payload(_payload_with_short_secret("5"))
    assert redacted["steps"][0]["args"]["qty"] == "[REDACTED:secret]"
    assert redacted["steps"][0]["result"] == "order total is 150 dollars"


def test_scrub_matches_whole_token_only() -> None:
    # A declared value of "25" must not corrupt the unrelated substring in "1250".
    payload = _payload_with_short_secret("25")
    redacted = redact_episode_payload(payload)
    assert redacted["steps"][0]["args"]["qty"] == "[REDACTED:secret]"
    # "1250" contains "25" but only as a substring, so it is left intact.
    assert redacted["steps"][0]["result"] == "order total is 1250 dollars"


def test_scrub_replaces_standalone_token() -> None:
    # The same value as a standalone token (surrounded by non-word chars) is scrubbed.
    payload = _payload_with_short_secret("25")
    payload["steps"][0]["result"] = "the quantity is 25 units"
    redacted = redact_episode_payload(payload)
    assert "25" not in redacted["steps"][0]["result"]
    assert REDACTION_MARKER in redacted["steps"][0]["result"]


def test_deeply_nested_result_is_scrubbed_without_recursion_error() -> None:
    # An adversarially deep nested result must not raise RecursionError, and the
    # secret echoed at the bottom must still be scrubbed (no silent depth-cap leak):
    # the traversal is iterative, so there is no depth at which redaction stops.
    deep: dict = {}
    cursor = deep
    for _ in range(5000):
        cursor["next"] = {}
        cursor = cursor["next"]
    cursor["leaf"] = "123-45-6789"
    payload = _payload_with_secret()
    payload["steps"][0]["result"] = deep
    redacted = redact_episode_payload(payload)
    assert redacted["steps"][0]["args"]["ssn"] == "[REDACTED:pii]"
    # Walk to the bottom of the rebuilt structure and confirm the secret is gone.
    node = redacted["steps"][0]["result"]
    for _ in range(5000):
        node = node["next"]
    assert node["leaf"] == REDACTION_MARKER
