"""Privacy-forward IDE redaction: secret scrub, entropy gate, no raw content."""

from __future__ import annotations

import uuid

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


def test_the_principal_utterance_is_scrubbed_like_the_goal() -> None:
    """It is the same class of data as the goal, so it inherits the goal's treatment."""
    redacted = redact_ide_episode(
        {
            "run_id": "r1",
            "goal": "write the README",
            "principal_utterance": "use the key sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA and British English",
            "steps": [],
        }
    )

    assert (
        "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        not in redacted["principal_utterance"]
    )
    assert "British English" in redacted["principal_utterance"]


def test_a_null_utterance_survives_redaction_as_null() -> None:
    """The shape production actually emits: _build_episode always sets the key."""
    redacted = redact_ide_episode(
        {
            "run_id": "r1",
            "goal": "write the README",
            "principal_utterance": None,
            "steps": [],
        }
    )

    assert redacted["principal_utterance"] is None


def test_an_utterance_is_scrubbed_but_never_clipped() -> None:
    """Length is decided at admission, which refuses; truncating here could invert meaning."""
    long_utterance = "we use British English " * 500

    redacted = redact_ide_episode(
        {
            "run_id": "r1",
            "goal": "g",
            "principal_utterance": long_utterance,
            "steps": [],
        }
    )

    assert redacted["principal_utterance"] == long_utterance


def _episode_with_step_ids(step_ids: list[str]) -> dict:
    return {
        "run_id": "bot:1",
        "goal": "fix the failing test",
        "steps": [
            {
                "id": step_id,
                "name": "Edit",
                "args": {"path": "a.py"},
                "status": "completed",
                "result": "ok",
                "error": None,
            }
            for step_id in step_ids
        ],
        "outcome": {
            "is_success": True,
            "total_steps": len(step_ids),
            "completed_steps": len(step_ids),
            "failed_steps": 0,
        },
        "source_framework": "cursor",
        "thread_id": None,
    }


def test_cursor_step_ids_stay_distinct() -> None:
    # A Cursor step id is a bare uuid4().hex, which cleared the entropy gate about
    # 83% of the time, so every step in an episode arrived as [REDACTED]. A step id
    # joins a decision to its outcome and is documented unique within the episode.
    step_ids = [uuid.uuid4().hex for _ in range(3)]


    steps = redact_ide_episode(_episode_with_step_ids(step_ids))["steps"]

    assert [step["id"] for step in steps] == step_ids
    assert len({step["id"] for step in steps}) == 3


def test_a_claude_code_step_id_is_preserved() -> None:
    # 30 characters against a 32-character rule, so it survives today by two
    # characters. Pinned so a format change is caught here rather than in prod.
    step_ids = ["toolu_01A09q90qw90lq917835lq9", "toolu_01LV4894wgjDjYHU6amS7JVT"]

    steps = redact_ide_episode(_episode_with_step_ids(step_ids))["steps"]

    assert [step["id"] for step in steps] == step_ids


def test_a_credential_shaped_step_id_is_re_minted_not_flattened() -> None:
    # This path must fail open, so refusing is unavailable. Re-minting drops the
    # suspect text while keeping the id unique, which the shared marker does not.
    leaked = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    clean = "toolu_01A09q90qw90lq917835lq9"

    steps = redact_ide_episode(_episode_with_step_ids([leaked, clean]))["steps"]

    got = [step["id"] for step in steps]
    assert got[0] != leaked and "ghp_" not in got[0]
    assert got[0] != REDACTION_MARKER, "a marker would collide with every other one"
    assert got[1] == clean, "a clean id is untouched"
    assert len(set(got)) == 2


def test_step_descriptive_fields_are_still_scrubbed() -> None:
    episode = _episode_with_step_ids(["toolu_01A09q90qw90lq917835lq9"])
    episode["steps"][0]["args"] = {"command": "export K=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"}

    steps = redact_ide_episode(episode)["steps"]

    assert "ghp_" not in str(steps[0]["args"])
