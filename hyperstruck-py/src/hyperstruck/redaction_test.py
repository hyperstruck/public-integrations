"""Client-side redaction: declared-field strip plus known-value scrub."""

from __future__ import annotations

import pytest

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
    known_credential_match,
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


def test_known_credential_match_finds_every_known_shape() -> None:
    for credential in (
        "sk-ABCDEFGHIJKLMNOPQRSTUV",
        "sk_live_ABCDEFGHIJ0123",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        "xoxb-0123456789-ABCDEFGHIJ",
        "Bearer ABCDEFGHIJKLMNOPQRST",
        "password=hunter2000",
        # Without a PEM case the private-key arm can be deleted with the suite
        # still green, which is the coverage this test's name promises.
        "-----BEGIN RSA PRIVATE KEY-----\nMIIabc123\n-----END RSA PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----\nMIIabc123\n-----END PRIVATE KEY-----",
    ):
        assert known_credential_match(credential) is not None, credential


@pytest.mark.parametrize(
    "spelling",
    [
        "myPassword=hunter2000",
        "DBPASSWORD=hunter2000",
        "XPassword=hunter2000",
        "myAPIKey=abcd1234",
        "db2Password=hunter2000",
    ],
)
def test_a_credential_key_is_found_however_it_is_capitalised(spelling: str) -> None:
    # The delimiter-only rule accepted all of these while the scrubber caught them.
    # Keying on the capital rather than a lowercase-to-uppercase hump is what covers
    # the all-caps and uppercase-preceded spellings, not just camelCase.
    assert known_credential_match(spelling) is not None, spelling


@pytest.mark.parametrize(
    "ordinary_word",
    ["notatoken=abcd", "nottapassword=abcd", "myTokenizer=abcdef"],
)
def test_a_key_name_buried_in_a_lowercase_word_is_not_a_credential(
    ordinary_word: str,
) -> None:
    assert known_credential_match(ordinary_word) is None, ordinary_word


@pytest.mark.parametrize(
    "glued_lowercase",
    ["mytoken=hunter2000", "thepassword=hunter2000", "userpwd=hunter2000"],
)
def test_the_glued_lowercase_key_is_a_known_and_accepted_ceiling(
    glued_lowercase: str,
) -> None:
    # The other half of the notatoken=abcd trade, pinned so it cannot pass as
    # coverage. These ARE credentials and the scrubber catches them; the key rule
    # accepts them because an all-lowercase glued key is indistinguishable from an
    # ordinary word containing the key name. Asserted alongside the scrubber's
    # opposite verdict so the asymmetry is visible rather than implied.
    assert known_credential_match(glued_lowercase) is None, glued_lowercase
    assert scrub_secrets(glued_lowercase) != glued_lowercase


def test_a_non_ascii_letter_reads_as_a_delimiter() -> None:
    # The delimiter test is ASCII-only, so an accented letter does not suppress a
    # key match while an ASCII one does. Arbitrary, and in the refusing direction,
    # so it is pinned rather than fixed.
    assert known_credential_match("cafétoken:abcd1234") is not None
    assert known_credential_match("übertoken:abcd1234") is None


def test_known_credential_match_ignores_the_entropy_arm() -> None:
    # The whole point of the helper: identifiers the generic 32+ char entropy rule
    # flattens are NOT credentials, so a caller refusing on this does not refuse
    # every descriptive identifier. Each fixture is verified to trip scrub_secrets,
    # so the test cannot pass by the fixtures having gone stale.
    for identifier in (
        "pr-305-review-round-2-fixes-and-followups",
        "superloop-supplier-code-of-conduct-review-2026-08-04",
        "learning-gate-observability-2026-08-02",
    ):
        assert scrub_secrets(identifier) != identifier, f"fixture must trip the scrubber: {identifier}"
        assert known_credential_match(identifier) is None, identifier


def test_a_uuid_is_below_the_entropy_gate_and_is_not_a_credential() -> None:
    # Recorded because the reasoning that produced the refusal defect said the
    # scrubber "cannot separate a leaked credential from a uuid". A uuid measures
    # 3.39 bits/char against the 3.5 gate, so it passes untouched. The population
    # that actually trips the gate is word-based ids, whose alphabet is wider.
    uuid_id = "550e8400-e29b-41d4-a716-446655440000"

    assert scrub_secrets(uuid_id) == uuid_id
    assert known_credential_match(uuid_id) is None


def test_known_credential_match_finds_a_credential_embedded_in_an_identifier() -> None:
    assert known_credential_match("run-ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345-retry") is not None


def test_known_credential_match_is_false_for_empty_and_short_text() -> None:
    assert known_credential_match("") is None
    assert known_credential_match("meeting-8220") is None


@pytest.mark.parametrize(
    "credential",
    [
        "AIzaSyD-1234567890abcdefghijklmnopqrstuv",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk",
        "github_pat_11ABCDEFG0abcdefghijklmnop_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghij",
        "ya29.A0ARrdaM-abcdefghijklmnopqrstuvwxyz",
        "SG.ABCDEFGHIJKLMNOPQRSTUV.ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "hf_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "npm_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ],
)
def test_a_prefixed_credential_the_entropy_arm_used_to_catch_is_refused(
    credential: str,
) -> None:
    # These reached the shape detector only via the entropy arm, so dropping it
    # for identifiers let them egress verbatim in a run id or a source_ref. Each
    # prefix is unambiguous, so covering them costs no false refusals.
    assert known_credential_match(credential) is not None, credential


@pytest.mark.parametrize(
    "quoted",
    ['password: "hunter2000"', "password='hunter2000'", 'api_key: "abcd1234"'],
)
def test_a_quoted_credential_value_is_scrubbed(quoted: str) -> None:
    # The value class excluded quotes, so it stopped at the opening quote and this
    # was the one shape NO layer caught: not the detector and not the scrubber.
    assert scrub_secrets(quoted) != quoted, quoted
    assert "hunter2000" not in scrub_secrets(quoted)


@pytest.mark.parametrize(
    "delimited",
    [
        # All four {s,r} x {live,test} spellings. Only sk_live_ used to be covered,
        # so narrowing the shape to sk_ or dropping "test" left the suite green
        # while a live credential egressed in a run id.
        "run-sk_live_ABCDEFGHIJ0123",
        "run-sk_test_ABCDEFGHIJ0123",
        "run-rk_live_ABCDEFGHIJ0123",
        "run-rk_test_ABCDEFGHIJ0123",
    ],
)
def test_every_stripe_style_spelling_is_refused(delimited: str) -> None:
    assert known_credential_match(delimited) is not None, delimited


@pytest.mark.parametrize(
    "glued",
    [
        "idghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        "myAKIAIOSFODNN7EXAMPLE",
        "prefixxoxb-0123456789-ABCDEFGHIJ",
    ],
)
def test_a_credential_glued_to_preceding_characters_is_still_found(glued: str) -> None:
    # A blanket token boundary over the whole alternation would miss these. Only
    # the two word-ambiguous shapes carry one, because only they collide with
    # ordinary words; these prefixes are ones no English word yields.
    assert known_credential_match(glued) is not None, glued


@pytest.mark.parametrize(
    "ordinary",
    [
        "risk-management-review-2026-08",
        "task-management-rollout-2026-08",
        "desk-checks-for-the-claims-lane",
        # The underscore spelling of the same collision: a word ending in "sk"/"rk"
        # followed by _live_/_test_ is the [sr]k_ shape exactly.
        "risk_live_monitoring_dashboard_2026",
        "desk_test_automation_pipeline_v2",
        "kiosk_live_deployment_checklist_2026",
        "notatoken=abcd",
    ],
)
def test_an_ordinary_identifier_that_looks_like_a_shape_is_not_a_credential(
    ordinary: str,
) -> None:
    # "risk-", "task-" and "desk-" all end in "sk" before a hyphenated tail, which
    # is the sk- shape exactly; "notatoken" contains the key name "token". Dropping
    # either boundary refuses all four, which is why both are applied per shape.
    assert known_credential_match(ordinary) is None, ordinary


@pytest.mark.parametrize(
    "camel_case_key",
    [
        "myPassword=hunter2000",
        "dbPassword=hunter2000",
        "userToken=abcd1234",
        "svcAuthToken=abcdefghijkl",
        "aPassphrase=letmein12",
    ],
)
def test_a_camel_case_credential_key_is_still_a_credential(camel_case_key: str) -> None:
    # A key name starts at a camelCase hump as well as after a delimiter. Requiring
    # a delimiter alone accepts these, which egresses a secret in a run id; that is
    # the direction that matters, so it is pinned separately from notatoken=abcd.
    assert known_credential_match(camel_case_key) is not None, camel_case_key


@pytest.mark.parametrize(
    "glued",
    [
        "xxsk-AbCdEf0123456789AbCdEf",
        "myrk_live_ABCDEFGHIJ0123",
        "myrk_test_ABCDEFGHIJ0123",
        "mysk_live_ABCDEFGHIJ0123",
        "mysk_test_ABCDEFGHIJ0123",
    ],
)
def test_the_glued_word_ambiguous_shapes_are_a_known_ceiling(glued: str) -> None:
    # Pins the TODO(ceiling) rather than leaving it as prose: a word-ambiguous
    # credential glued to letters is indistinguishable from an ordinary id like
    # "risk-management-review-2026-08", so it is knowingly accepted. If this ever
    # starts failing, the ambiguity was resolved and the ceiling comment goes too.
    assert known_credential_match(glued) is None, glued


@pytest.mark.parametrize(
    "descriptive",
    [
        # Each was refused when the added shapes carried round-number floors and no
        # boundary: "SG." can end an ordinary word and github_pat_ admits
        # underscores, so both swallowed hyphen/underscore descriptive tails.
        "SG.performance_review_2026.engineering_summary_notes",
        "MSG.performance_review_2026.engineering_summary_notes",
        "release-SG.candidate_build_2026.integration_test_matrix",
        "github_pat_migration_notes_for_the_team",
    ],
)
def test_an_added_shape_does_not_refuse_a_descriptive_identifier(
    descriptive: str,
) -> None:
    assert known_credential_match(descriptive) is None, descriptive


def test_the_added_floors_sit_below_the_real_credential_and_above_prose() -> None:
    # Asserting only that a real key is refused passes at any floor at or below the
    # real length, so it cannot catch a floor raised too far. Each floor is pinned
    # from both sides: the real credential refuses, one character under does not.
    assert known_credential_match("SG." + "A" * 22 + "." + "B" * 43) is not None
    assert known_credential_match("SG." + "A" * 19 + "." + "B" * 30) is None
    assert known_credential_match("github_pat_" + "A" * 82) is not None
    assert known_credential_match("github_pat_" + "A" * 49) is None


def test_a_longer_google_lookalike_redacts_whole() -> None:
    # The shape was fixed-length, so a longer token matched only its first 39
    # characters and left the tail in the text.
    assert scrub_secrets("AIza" + "S" * 35 + "XXXXXXXXXXXX") == REDACTION_MARKER


def test_a_quoted_value_never_swallows_a_newline() -> None:
    # The unquoted class is whitespace-bounded so it can only eat one token. A
    # quoted one is bounded by the next quote, which on a clipped stderr can be
    # lines away, and taking those lines destroys the failure detail.
    stderr = 'bash: setting password: "x\nERROR at line 12 in "config.yaml"\nstack frame 3'

    assert scrub_secrets(stderr) == stderr


@pytest.mark.parametrize(
    ("fragment", "secret"),
    [
        ('{"password": "hunter2000"}', "hunter2000"),
        ("{'api_key': 'sk_live_xyz1'}", "sk_live_xyz1"),
    ],
)
def test_a_quoted_key_and_value_are_scrubbed(fragment: str, secret: str) -> None:
    # A stringified JSON or YAML fragment in a tool error is the likely carrier,
    # and the key's own closing quote used to sit between it and the colon. Each
    # case names its own secret, so no assertion passes for an unrelated reason.
    assert secret not in scrub_secrets(fragment)


def test_an_unterminated_quoted_value_is_still_scrubbed() -> None:
    # Clipping a tool result is exactly what produces an unterminated quote, and
    # the closing quote was required, so the value leaked whole. The newline bound
    # keeps the redaction to its own line.
    clipped = 'password: "hunter2000\nERROR at line 12\nstack frame 3'

    scrubbed = scrub_secrets(clipped)

    assert "hunter2000" not in scrubbed
    assert "ERROR at line 12" in scrubbed, "the failure detail must survive"
    assert "stack frame 3" in scrubbed
