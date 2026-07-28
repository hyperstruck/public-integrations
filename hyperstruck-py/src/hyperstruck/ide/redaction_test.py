"""Privacy-forward IDE redaction: secret scrub, entropy gate, no raw content."""

from __future__ import annotations

from hyperstruck.ide.constants import (
    MAX_BOUNDARY_GOAL_CHARS,
    MAX_RESULT_CHARS,
    TRUNCATION_MARKER,
)
from hyperstruck.ide.redaction import _clip, clip_goal, clip_result, redact_ide_episode
from hyperstruck.redaction import REDACTION_MARKER, scrub_secrets


def test_known_credential_shapes_scrubbed() -> None:
    assert (
        scrub_secrets("token sk-ABCDEFGHIJKLMNOPQRSTUV end")
        == f"token {REDACTION_MARKER} end"
    )
    assert scrub_secrets("AKIAIOSFODNN7EXAMPLE") == REDACTION_MARKER
    assert REDACTION_MARKER in scrub_secrets("ghp_0123456789abcdefghijABCDEFGHIJ")
    assert REDACTION_MARKER in scrub_secrets(
        "Authorization: Bearer abcdef0123456789ABCDEF"
    )


def test_pem_block_scrubbed() -> None:
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB\nkey\n-----END RSA PRIVATE KEY-----"
    )
    assert scrub_secrets(pem) == REDACTION_MARKER


def test_prose_preserved() -> None:
    prose = "the quick brown fox jumps over the lazy dog several times in a row"
    assert scrub_secrets(prose) == prose


def test_high_entropy_token_scrubbed_low_entropy_preserved() -> None:
    # A random 40-char base64-ish key clears the entropy gate.
    assert scrub_secrets("xY7kP2mQ9vB3nL5wR8tZ1cF4hJ6dG0sA2bC5eK9") == REDACTION_MARKER
    # A long but low-entropy repetitive token does not.
    assert scrub_secrets("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") != REDACTION_MARKER


def test_clip_result_truncates() -> None:
    big = "x" * (MAX_RESULT_CHARS + 500)
    clipped = clip_result(big)
    assert clipped.endswith(TRUNCATION_MARKER)
    assert len(clipped) == MAX_RESULT_CHARS  # the marker counts toward the ceiling
    assert clip_result(None) is None


def test_clip_goal_holds_the_platform_bound() -> None:
    clipped = clip_goal("x" * (MAX_BOUNDARY_GOAL_CHARS + 1))
    assert len(clipped) == MAX_BOUNDARY_GOAL_CHARS
    assert clipped.endswith(TRUNCATION_MARKER)
    assert clip_goal("x" * MAX_BOUNDARY_GOAL_CHARS) == "x" * MAX_BOUNDARY_GOAL_CHARS
    assert clip_goal("") == ""


def test_clip_never_exceeds_a_limit_too_small_for_the_marker() -> None:
    for limit in range(0, len(TRUNCATION_MARKER) + 2):
        assert len(_clip("abcdefghijklmnopqrstuvwxyz", limit)) == limit


def test_redact_ide_episode_clips_a_goal_the_scrub_grew_over_the_bound() -> None:
    # A short key=value credential: the marker substituted in is longer than the
    # value it replaces, so this goal grows past the bound during the scrub.
    secret = "password=abcd "
    goal = secret + "x" * (MAX_BOUNDARY_GOAL_CHARS - len(secret))
    assert len(goal) == MAX_BOUNDARY_GOAL_CHARS
    redacted = redact_ide_episode({"goal": goal, "steps": []})
    assert redacted["goal"].startswith(f"password={REDACTION_MARKER}")
    assert len(redacted["goal"]) == MAX_BOUNDARY_GOAL_CHARS


def test_redact_ide_episode_scrubs_secrets_everywhere() -> None:
    payload = {
        "run_id": "agent:1",
        "goal": "use the key sk-ABCDEFGHIJKLMNOPQRSTUV",
        "steps": [
            {
                "id": "1",
                "name": "bash",
                "args": {"command": "export K=sk-ABCDEFGHIJKLMNOPQRSTUV"},
                "status": "completed",
                "result": "ok sk-ABCDEFGHIJKLMNOPQRSTUV",
                "error": None,
            },
        ],
        "outcome": {
            "is_success": True,
            "total_steps": 1,
            "completed_steps": 1,
            "failed_steps": 0,
        },
        "source_framework": "claude-code",
        "thread_id": None,
    }
    redacted = redact_ide_episode(payload)
    assert "sk-ABCDEFGHIJKLMNOPQRSTUV" not in str(redacted)
    # The input is not mutated.
    assert "sk-ABCDEFGHIJKLMNOPQRSTUV" in payload["goal"]


def test_run_id_and_thread_id_preserved() -> None:
    # The run_id uuid tail clears the entropy gate; it must NOT be scrubbed, or
    # the server cannot match the offer log and reinforce credits nothing.
    run_id = "acme/app:sess9:" + "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    payload = {
        "run_id": run_id,
        "goal": "use sk-ABCDEFGHIJKLMNOPQRSTUV now",
        "steps": [
            {
                "id": "1",
                "name": "bash",
                "args": {},
                "status": "completed",
                "result": None,
                "error": None,
            }
        ],
        "outcome": {
            "is_success": True,
            "total_steps": 1,
            "completed_steps": 1,
            "failed_steps": 0,
        },
        "source_framework": "claude-code",
        "thread_id": "thread:" + "f0e1d2c3b4a5968778695a4b3c2d1e0f",
    }
    redacted = redact_ide_episode(payload)
    assert redacted["run_id"] == run_id  # identifier untouched
    assert redacted["thread_id"] == payload["thread_id"]
    assert "[REDACTED]" not in redacted["run_id"]
    assert "sk-ABCDEFGHIJKLMNOPQRSTUV" not in redacted["goal"]  # secret still scrubbed


def test_kv_assignment_value_redacted() -> None:
    out = scrub_secrets("DB_PASSWORD=hunter2plain")
    assert "hunter2plain" not in out
    assert out.lower().startswith("db_password=")  # key kept, value redacted
    assert "topsecret" not in scrub_secrets("token: topsecret123")
