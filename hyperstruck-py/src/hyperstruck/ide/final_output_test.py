"""Reading the answer the assistant gave out of the editor's own transcript."""

from __future__ import annotations

import json

from hyperstruck.ide.final_output import MAX_FINAL_OUTPUT_CHARS, final_assistant_text


def _line(record: dict) -> str:
    return json.dumps(record) + "\n"


def _assistant(*blocks: dict) -> str:
    return _line({"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}})


def _text(value: str) -> dict:
    return {"type": "text", "text": value}


def _prompt(value: str = "do the thing") -> str:
    """A turn opening: the person typing. This is the boundary the reader bounds itself to, so every
    fixture that expects an answer has to start one, exactly as a real transcript does."""
    return _line({"type": "user", "message": {"role": "user", "content": value}})


def _tool_result(value: str = "...") -> str:
    """A tool result, which the editor writes back under the user role. It is the turn continuing,
    not a new one starting, and reading it as a boundary would end every turn at its first tool."""
    return _line(
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": value}]}}
    )


def test_the_last_assistant_message_is_the_answer_and_the_earlier_ones_are_not(tmp_path):
    """The closing block, never a join of them.

    An assistant emits text between tool calls as well as at the end, and that mid-turn text is
    thinking out loud on the way to an answer. Joining them would feed the obligation lane "I'll
    check the depot schedule next", which is a plan for the following ten seconds rather than a
    commitment to anybody, and that is the largest false-positive class the manifesto names.
    """
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _line({"type": "user", "message": {"content": "check the depot schedule"}})
        + _assistant(_text("I'll check the depot schedule next."))
        + _line({"type": "user", "message": {"content": [{"type": "tool_result", "content": "..."}]}})
        + _assistant(_text("I will confirm the shipment volumes by Friday.")),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "I will confirm the shipment volumes by Friday."


def test_only_text_blocks_of_that_message_are_read(tmp_path):
    """A tool-use block is the assistant acting rather than speaking, and a thinking block is
    explicitly not addressed to anybody. Either one behind a provenance class that says the agent
    bound itself to the reader would be storing the trace as a promise."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt()
        + _assistant(
            {"type": "thinking", "thinking": "I should promise to send the file"},
            _text("Here is the summary."),
            {"type": "tool_use", "name": "Write", "input": {}},
            _text("I will send it by Friday."),
        ),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "Here is the summary.\n\nI will send it by Friday."


def test_a_string_content_message_still_reads(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt() + _line({"type": "assistant", "message": {"content": "I will send it by Friday."}}),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "I will send it by Friday."


def test_every_way_the_read_can_fail_answers_with_nothing(tmp_path):
    """An absent value costs nothing that can be told apart from a turn whose answer held no
    commitments, so there is no state worth reporting and nothing worth raising over. It is on the
    stop path of every turn and must never be able to cost a turn its episode."""
    assert final_assistant_text("") == ""
    assert final_assistant_text(None) == ""
    assert final_assistant_text(str(tmp_path / "missing.jsonl")) == ""
    broken = tmp_path / "broken.jsonl"
    broken.write_text(
        _prompt() + '{"type": "assistant" not json\n' + _line({"type": "assistant"}) + '["assistant"]\n',
        encoding="utf-8",
    )
    assert final_assistant_text(str(broken)) == ""


def test_the_answer_is_clipped_to_the_boundary_s_bound(tmp_path):
    """Clipped here rather than rejected there: the API bounds the field, a 4xx is terminal to the
    flush retry, and it would cost the whole episode rather than this one field."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(_prompt() + _assistant(_text("x" * (MAX_FINAL_OUTPUT_CHARS + 100))), encoding="utf-8")
    assert len(final_assistant_text(str(path))) == MAX_FINAL_OUTPUT_CHARS


def test_the_answer_is_found_without_reading_the_whole_session(tmp_path, monkeypatch):
    """The tail read is the point: this runs on every stop against a file that only grows.

    Asserted by what was READ rather than by the answer, because the answer is identical either way
    and that is exactly how a cost regression here would go unnoticed.
    """
    from hyperstruck.ide import transcript as transcript_module

    path = tmp_path / "transcript.jsonl"
    filler = _line({"type": "user", "message": {"content": "x" * 4000}})
    path.write_text(filler * 400 + _assistant(_text("I will confirm the volumes by Friday.")), encoding="utf-8")
    monkeypatch.setattr(transcript_module, "TAIL_BYTES", 64 * 1024)
    monkeypatch.setattr("hyperstruck.ide.final_output.TAIL_BYTES", 64 * 1024)

    read: list[int] = []
    original = transcript_module.iter_lines

    def _counting(*args, **kwargs):
        count = 0
        for line in original(*args, **kwargs):
            count += 1
            yield line
        read.append(count)

    monkeypatch.setattr("hyperstruck.ide.final_output.iter_lines", _counting)

    assert final_assistant_text(str(path)) == "I will confirm the volumes by Friday."
    assert len(read) == 1, "the tail answered, so the whole file must not have been scanned as well"
    assert read[0] < 400, f"read {read[0]} lines of a 401-line transcript; the tail bound did nothing"


def test_an_answer_further_back_than_the_tail_is_still_found(tmp_path, monkeypatch):
    """The fallback, and why the tail read is not a silent trade.

    A turn can compose its answer and then run tools that return megabytes, putting the closing
    message outside the tail. Answering "" there would be a new way to lose a commitment that the
    unbounded read never had, so the bounded read is an optimisation of the common case only.
    """
    path = tmp_path / "transcript.jsonl"
    trailing = _line({"type": "user", "message": {"content": [{"type": "tool_result", "content": "y" * 4000}]}})
    path.write_text(
        _prompt() + _assistant(_text("I will send the report by Friday.")) + trailing * 200, encoding="utf-8"
    )
    monkeypatch.setattr("hyperstruck.ide.final_output.TAIL_BYTES", 4096)

    assert final_assistant_text(str(path)) == "I will send the report by Friday."


def test_a_partial_record_at_the_tail_boundary_is_not_read_as_one(tmp_path, monkeypatch):
    """A byte offset lands mid-record, and half a JSON object is not a record. The reader drops the
    line it landed inside; without that, the first thing every tail read sees is a parse error."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt()
        + _assistant(_text("stale answer that must not win"))
        + _assistant(_text("I will confirm the volumes by Friday.")),
        encoding="utf-8",
    )
    # Land the offset inside the first record.
    monkeypatch.setattr("hyperstruck.ide.final_output.TAIL_BYTES", len(path.read_bytes()) - 40)

    assert final_assistant_text(str(path)) == "I will confirm the volumes by Friday."


def test_the_wire_bound_is_the_one_the_boundary_declares() -> None:
    """Re-exported from ``constants`` rather than declared here: it is a fact about the boundary and
    redaction reads it too, so having it live in the transcript reader made redaction import a file
    reader to learn a number."""
    from hyperstruck.ide import constants

    assert MAX_FINAL_OUTPUT_CHARS is constants.MAX_FINAL_OUTPUT_CHARS


# -- the turn boundary -------------------------------------------------------------------------
#
# The reader answers for THIS turn or it answers nothing. A transcript is one append-only file for
# the whole session, so before it was bounded a turn that composed no prose handed the previous
# turn's answer to this run's episode, and the lane wrote that turn's commitments onto the shelf a
# second time, dated to now, under this agent's name. That is the one path in this work that reaches
# a paying customer today.


def test_a_turn_that_composed_nothing_does_not_inherit_the_previous_turn_s_answer(tmp_path):
    """The defect, stated as a fixture: turn one answers, turn two runs a tool and stops.

    The newest assistant text in the file is turn one's, and it is not this turn's. Reporting it
    puts a promise on the shelf that nobody made in this run.
    """
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("I will confirm the shipment volumes by Friday."))
        + _prompt("now just run the linter")
        + _tool_result("all clean"),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == ""


def test_a_turn_that_composed_text_after_one_that_did_reads_only_its_own(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("I will confirm the shipment volumes by Friday."))
        + _prompt("and the linter?")
        + _tool_result("all clean")
        + _assistant(_text("The linter is clean. I will land the fix on Monday.")),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "The linter is clean. I will land the fix on Monday."


def test_a_tool_result_is_not_a_turn_boundary(tmp_path):
    """A ``user`` record is two different things wearing one type, and only one of them opens a
    turn. Reading a tool result as a boundary would end every turn at its first tool call and
    harvest nothing from any turn that used one, which is nearly all of them."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("Checking the schedule now."))
        + _tool_result("depot: 14 pallets")
        + _assistant(_text("I will confirm the shipment volumes by Friday.")),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "I will confirm the shipment volumes by Friday."


def test_a_subagent_s_own_conversation_is_neither_the_answer_nor_a_boundary(tmp_path):
    """A sidechain is a subagent talking to itself and the person was never shown it. Read as the
    answer it is a commitment nobody was made; read as a boundary it ends the turn early and loses
    the real one."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("I will confirm the shipment volumes by Friday."))
        + _line(
            {
                "type": "user",
                "isSidechain": True,
                "message": {"role": "user", "content": "sub-task: read the manifest"},
            }
        )
        + _line(
            {
                "type": "assistant",
                "isSidechain": True,
                "message": {"role": "assistant", "content": [{"type": "text", "text": "I will email the manifest."}]},
            }
        ),
        encoding="utf-8",
    )
    assert final_assistant_text(str(path)) == "I will confirm the shipment volumes by Friday."


def test_a_boundary_that_cannot_be_established_reads_nothing_rather_than_guessing(tmp_path, monkeypatch):
    """The failure direction, chosen rather than fallen into.

    The scan is bounded twice over, so it can run out of records having found neither this turn's
    prose nor the boundary proving there was none. In that state the previous turn's answer is
    sitting right there and is the wrong answer, so the reader gives up. Nothing is lost that was
    not already optional; a false obligation is not.
    """
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("I will confirm the shipment volumes by Friday."))
        + _prompt("now run every check")
        + _tool_result("ok") * 40,
        encoding="utf-8",
    )
    # A window too small to reach back past this turn's own tool results to the prompt that opened
    # it. Both the tail read and the whole-file read run out inside them.
    monkeypatch.setattr("hyperstruck.ide.final_output._TAIL_CANDIDATES", 8)

    assert final_assistant_text(str(path)) == ""


def test_a_transcript_holding_no_opening_prompt_at_all_reads_nothing(tmp_path):
    """The same unbounded state reached the other way: a file whose start this read did see, and
    which holds no turn opening anywhere in it. Nothing here says which turn the prose belongs to."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(_tool_result("ok") + _tool_result("ok"), encoding="utf-8")
    assert final_assistant_text(str(path)) == ""


def test_the_bounded_empty_answer_does_not_pay_for_a_second_whole_file_read(tmp_path, monkeypatch):
    """A turn that genuinely composed nothing is the common case on a tool-only turn, and it is
    settled by the tail. Re-reading the whole session for it would pay the unbounded cost on exactly
    the turns with nothing to give, which is the regression the tail read exists to prevent."""
    from hyperstruck.ide import transcript as transcript_module

    path = tmp_path / "transcript.jsonl"
    path.write_text(
        _prompt("check the depot schedule")
        + _assistant(_text("I will confirm the shipment volumes by Friday."))
        + _prompt("now just run the linter")
        + _tool_result("all clean"),
        encoding="utf-8",
    )

    reads: list[int] = []
    original = transcript_module.iter_lines

    def _counting(*args, **kwargs):
        count = 0
        for line in original(*args, **kwargs):
            count += 1
            yield line
        reads.append(count)

    monkeypatch.setattr("hyperstruck.ide.final_output.iter_lines", _counting)

    assert final_assistant_text(str(path)) == ""
    assert len(reads) == 1, "the tail settled the turn, so the whole file must not be read again"
