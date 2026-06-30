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
        "outcome": {
            "is_success": True,
            "total_steps": 2,
            "completed_steps": 2,
            "failed_steps": 0,
        },
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
        "outcome": {
            "is_success": True,
            "total_steps": 1,
            "completed_steps": 1,
            "failed_steps": 0,
        },
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


# ---------------------------------------------------------------------------
# Tiered free-text detector (secrets + validated structured PII)
# ---------------------------------------------------------------------------

from hyperstruck.redaction import (  # noqa: E402
    RedactionPolicy,
    redact_free_text,
    redact_text,
    scrub_secrets,
)


def test_secret_becomes_tagged_placeholder() -> None:
    out = redact_text("my key is sk-ABCDEFGHIJKLMNOPQRSTUV here")
    assert "sk-ABCDEFGHIJKLMNOPQRSTUV" not in out
    assert "<SECRET_1>" in out


def test_repeated_secret_shares_one_placeholder() -> None:
    key = "AKIAIOSFODNN7EXAMPLE"
    out = redact_text(f"{key} and again {key}")
    assert out.count("<SECRET_1>") == 2
    assert "<SECRET_2>" not in out


def test_email_redacted_to_placeholder() -> None:
    out = redact_text("write to ada@example.com please")
    assert "ada@example.com" not in out
    assert "<EMAIL_1>" in out


def test_credit_card_validated_by_luhn() -> None:
    # A Luhn-valid card is redacted; a same-length non-Luhn number is left alone.
    assert "<CARD_1>" in redact_text("card 4111 1111 1111 1111 on file")
    out = redact_text("order number 4111 1111 1111 1112 shipped")
    assert "<CARD" not in out
    assert "4111 1111 1111 1112" in out


def test_iban_validated_by_mod97() -> None:
    assert "<IBAN_1>" in redact_text("pay GB82WEST12345698765432 today")
    assert "<IBAN" not in redact_text("ref GB00WEST12345698765432 here")


def test_ssn_and_ip_redacted() -> None:
    out = redact_text("ssn 123-45-6789 from host 192.168.1.5")
    assert "<SSN_1>" in out
    assert "<IP_1>" in out
    assert "192.168.1.5" not in out


def test_invalid_ip_octet_not_redacted() -> None:
    out = redact_text("version 999.999.0.1 of the build")
    assert "<IP" not in out
    assert "999.999.0.1" in out


def test_phone_redacted_but_small_number_preserved() -> None:
    assert "<PHONE_1>" in redact_text("call +1 415-555-0132 now")
    # A short bare integer is not a phone number and must survive.
    assert "<PHONE" not in redact_text("we shipped 250 units")


def test_prose_survives() -> None:
    prose = "the agent prefers the bulk endpoint for large reads"
    assert redact_text(prose) == prose


def test_ner_absent_degrades_to_tier_one() -> None:
    # Requesting NER with no backend installed must still apply Tier 1, not crash.
    policy = RedactionPolicy(is_ner_enabled=True)
    out = redact_text(
        "token sk-ABCDEFGHIJKLMNOPQRSTUV for ada@example.com", policy=policy
    )
    assert "<SECRET_1>" in out
    assert "<EMAIL_1>" in out


def test_custom_ner_hook_runs() -> None:
    policy = RedactionPolicy(
        is_ner_enabled=True, ner_hook=lambda t: t.replace("Ada Lovelace", "<NAME_1>")
    )
    out = redact_text("Ada Lovelace sent ada@example.com", policy=policy)
    assert "<NAME_1>" in out
    assert "<EMAIL_1>" in out


def test_redact_free_text_preserves_identifiers() -> None:
    payload = {
        "run_id": "bot:abc-123-def",
        "goal": "email ada@example.com about the deploy",
        "source_framework": "mcp:test",
        "steps": [
            {
                "id": "step-1",
                "status": "completed",
                "name": "send_email",
                "args": {"to": "ada@example.com"},
                "result": "sent",
            }
        ],
        "outcome": {"is_success": True},
    }
    redacted = redact_free_text(payload)
    # Identifiers untouched (the boundary keys its offer log on run_id).
    assert redacted["run_id"] == "bot:abc-123-def"
    assert redacted["source_framework"] == "mcp:test"
    assert redacted["steps"][0]["id"] == "step-1"
    assert redacted["steps"][0]["status"] == "completed"
    # Free text scrubbed, consistently across the payload.
    assert "ada@example.com" not in redacted["goal"]
    assert "<EMAIL_1>" in redacted["goal"]
    assert "ada@example.com" not in redacted["steps"][0]["args"]["to"]
    # Input not mutated.
    assert payload["goal"] == "email ada@example.com about the deploy"


def test_scrub_secrets_default_marker_unchanged_for_adapters() -> None:
    # The IDE path relies on the bare marker; the shared core must still produce it.
    assert scrub_secrets("AKIAIOSFODNN7EXAMPLE") == REDACTION_MARKER


def test_short_secret_under_sensitive_key_is_redacted() -> None:
    # A short, low-entropy value the secrets tier would miss in free text must
    # still be redacted when it sits under a sensitive key name in a payload.
    payload = {"steps": [{"name": "call", "args": {"api_key": "Xk93jZ"}}]}
    out = redact_free_text(payload)
    assert "Xk93jZ" not in str(out)
    assert "<SECRET_1>" == out["steps"][0]["args"]["api_key"]


def test_sensitive_key_matches_common_spellings() -> None:
    payload = {"password": "p@ss", "authToken": "abc123", "note": "fine"}
    out = redact_free_text(payload)
    assert out["password"].startswith("<SECRET")
    assert out["authToken"].startswith("<SECRET")
    assert out["note"] == "fine"


def test_redact_free_text_handles_deep_nesting_without_recursion_error() -> None:
    # The host-reported write path is arbitrarily deep; the walk must be iterative.
    deep: dict = {}
    cursor = deep
    for _ in range(6000):
        cursor["next"] = {}
        cursor = cursor["next"]
    cursor["leaf"] = "ada@example.com"
    out = redact_free_text({"goal": "g", "steps": [deep]})
    node = out["steps"][0]
    for _ in range(6000):
        node = node["next"]
    assert node["leaf"] != "ada@example.com"
    assert "<EMAIL" in node["leaf"]




def test_namespaced_sensitive_keys_are_redacted() -> None:
    # The anchored regex used to miss these common spellings; the fragment match
    # now catches them.
    payload = {
        "db_password": "hunter2",
        "access_token": "abc123",
        "client_secret": "xyz789",
        "openai_api_key": "shortkey",
        "harmless": "keep me",
    }
    out = redact_free_text(payload)
    assert out["db_password"].startswith("<SECRET")
    assert out["access_token"].startswith("<SECRET")
    assert out["client_secret"].startswith("<SECRET")
    assert out["openai_api_key"].startswith("<SECRET")
    assert out["harmless"] == "keep me"


def test_sensitive_key_propagates_into_nested_dict() -> None:
    # A secret nested under a sensitive key is redacted even though its own inner
    # key is innocuous.
    payload = {"credential": {"value": "shortlowentropy", "kind": "bearer"}}
    out = redact_free_text(payload)
    assert out["credential"]["value"].startswith("<SECRET")
    assert out["credential"]["kind"].startswith("<SECRET")
