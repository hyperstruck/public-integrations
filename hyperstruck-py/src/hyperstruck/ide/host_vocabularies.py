"""What each host declares about itself: its terminal statuses and its own tools.

A native status is a host protocol value, so its meaning belongs beside the host
adapter rather than in one shared set every source reads. The shared set is how
the current defect arrived: membership decided failure and *non-membership
decided success*, so a CI run killed by a ``timeout`` was credited.

Resolution happens here, where the source is already known, and the resolved
vocabulary is passed into outcome resolution as data. That keeps the outcome path
free of any branch on host identity while still letting each host speak for
itself.

A source absent from this table gets the empty vocabulary and abstains on every
status. That is deliberate and it is a real cliff, so a host is declared here in
the same change that adds the host.

TODO(ceiling): no host documents its terminal statuses to this client, and none of
the installed hooks passes ``--native-status``, so these declarations inherit the
membership the previous shared set already asserted rather than being verified
against a host protocol. What has changed is the default: an undeclared status now
abstains instead of counting as success. Revisit each set against the host's own
documentation when a host starts reporting a status this client can observe.
"""

from __future__ import annotations

from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    SOURCE_OPENHANDS,
    STATUS_COMPLETED,
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
    STEP_KIND_READ,
)
from hyperstruck.ide.outcome import EMPTY_VOCABULARY, NativeStatusVocabulary

_INHERITED_VOCABULARY = NativeStatusVocabulary(
    success=frozenset({STATUS_COMPLETED}),
    failure=frozenset({"aborted", "error", "cancelled", "failed"}),
)

_SOURCE_VOCABULARIES = {
    SOURCE_CLAUDE_CODE: _INHERITED_VOCABULARY,
    SOURCE_CURSOR: _INHERITED_VOCABULARY,
    SOURCE_OPENHANDS: _INHERITED_VOCABULARY,
}


def vocabulary_for(source: str) -> NativeStatusVocabulary:
    """The declared status vocabulary for one source, empty when it declared none."""
    return _SOURCE_VOCABULARIES.get(source, EMPTY_VOCABULARY)


# What each host's own built-in tools do, by the exact names that host publishes.
#
# This is protocol translation, not a judgement about language. Every key is a literal
# identifier from one host's documented tool list, matched whole and only for that host;
# nothing here reads a name for what it might mean. That is the whole difference from the
# substring table this replaces, which decided ``STEP_KIND_EDIT`` for any tool whose name
# happened to contain "edit" and dropped every tool from every MCP server into the one
# kind the observe gate refuses.
#
# It covers a host's own tools only. Anything a server contributes at runtime is declared
# through the registration store, and a tool neither source declares is material.
#
# Completeness matters here in one direction only, and it is the direction that bites. The
# material default is meant for tools nobody classified; a *host's own* bookkeeping tool
# falling through to it lets a turn of pure planning clear the observe gate on TodoWrite
# calls alone. So a host's read-only built-ins are declared even though declaring them
# changes nothing about how they are gated: leaving one out is what changes something.
_CLAUDE_CODE_TOOLS = {
    "Bash": STEP_KIND_COMMAND,
    "BashOutput": STEP_KIND_READ,
    "Edit": STEP_KIND_EDIT,
    "ExitPlanMode": STEP_KIND_READ,
    "Glob": STEP_KIND_READ,
    "Grep": STEP_KIND_READ,
    "KillShell": STEP_KIND_COMMAND,
    "NotebookEdit": STEP_KIND_EDIT,
    "Read": STEP_KIND_READ,
    "Task": STEP_KIND_READ,
    "TodoWrite": STEP_KIND_READ,
    "WebFetch": STEP_KIND_READ,
    "WebSearch": STEP_KIND_READ,
    "Write": STEP_KIND_EDIT,
}

_CURSOR_TOOLS = {
    # The names Cursor's hooks report, beside the agent's own tool names below.
    "Delete": STEP_KIND_EDIT,
    "Grep": STEP_KIND_READ,
    "Read": STEP_KIND_READ,
    "Shell": STEP_KIND_COMMAND,
    "Task": STEP_KIND_READ,
    "Write": STEP_KIND_EDIT,
    "codebase_search": STEP_KIND_READ,
    "delete_file": STEP_KIND_EDIT,
    "edit_file": STEP_KIND_EDIT,
    "file_search": STEP_KIND_READ,
    "grep_search": STEP_KIND_READ,
    "list_dir": STEP_KIND_READ,
    "read_file": STEP_KIND_READ,
    "run_terminal_cmd": STEP_KIND_COMMAND,
    "search_replace": STEP_KIND_EDIT,
}

_SOURCE_TOOLS: dict[str, dict[str, str]] = {
    SOURCE_CLAUDE_CODE: _CLAUDE_CODE_TOOLS,
    SOURCE_CURSOR: _CURSOR_TOOLS,
}


def declared_kind(source: str, tool_name: str) -> str | None:
    """The step kind this host declares for one of its own tools, or nothing.

    Abstains on an undeclared name, like the status vocabularies above: a host that has
    not been declared here says nothing about its tools rather than inheriting another
    host's, and an abstention leaves the tool to the registration store and then to the
    material default.
    """
    return _SOURCE_TOOLS.get(source, {}).get(tool_name)


# Whether a host's prompt hook can put text in front of the model at all.
#
# Claude Code's ``UserPromptSubmit`` returns an ``additionalContext`` block the editor
# injects. Cursor's ``beforeSubmitPrompt`` cannot: its injection rides ``postToolUse``,
# which is why ``_emit_tool_context`` has a second envelope shape for it. Emitting the
# Claude Code envelope there is worse than emitting nothing, because the host discards it
# and the turn would still have recorded the exposure as real.
_PROMPT_INJECTING_SOURCES = frozenset({SOURCE_CLAUDE_CODE})


def is_prompt_injectable(source: str) -> bool:
    """Whether this host will show text emitted from the prompt hook.

    Abstains to ``False`` on an undeclared host, like every other table here: a host that
    has not been declared cannot be assumed to accept another host's envelope, and the cost
    of abstaining is a feature that stays off rather than a claim that turns out false.
    """
    return source in _PROMPT_INJECTING_SOURCES


# Hosts that deliver a FAILED tool call's result as a plain string and a successful one as a
# structured object. Measured across 3,170 Claude Code transcripts the separation is exact:
# all 2,509 failures were string-shaped, none was object-shaped, and every string-shaped
# result that was not a failure was a JSON payload from an MCP tool.
#
# Declared per host rather than applied everywhere, because it is a protocol fact about one
# host and the cost of over-reaching is severe: on a host where a successful read returns its
# file body as a string, the same rule would call that read a failure and treat the body as
# an error message. Undeclared hosts abstain, like every other table here.
_STRING_RESULT_MEANS_FAILURE = frozenset({SOURCE_CLAUDE_CODE})


def is_string_result_a_failure(source: str) -> bool:
    """Whether this host signals a failed call by returning its result as a plain string."""
    return source in _STRING_RESULT_MEANS_FAILURE


# The generic framing a host wraps a failed result in, as literal protocol strings that host
# emits. These are envelopes around whatever the program printed: Claude Code leads every
# failed result with ``Error:`` and an ``Exit code N`` line, and what follows one is the
# program's own output, so removing the frame reveals text that no tier licenses reading.
# They are declared so the frame itself is never mistaken for the failure's name.
_SOURCE_FAILURE_FRAMING = {
    SOURCE_CLAUDE_CODE: (r"^Error\s*:?\s*", r"^Exit code \d+\s*:?\s*"),
}


def generic_failure_framing(source: str) -> tuple[str, ...]:
    """The generic prefixes this host wraps a failed result in, empty when undeclared.

    These license nothing. Named apart from :func:`host_authored_framing` because the two
    were near-synonyms once and the difference between them is a privacy control: wiring a
    caller to the wrong one leaks silently, since both return plausible-looking prefixes.
    """
    return _SOURCE_FAILURE_FRAMING.get(source, ())


# The frames introducing a message the host itself composed, rather than an envelope around
# a program's output. The distinction is a privacy control and not a parsing convenience:
# what follows a protocol frame is drawn from the host's own fixed vocabulary, so masking
# what varies inside it leaves a template that recurs across machines. What follows a
# generic frame is arbitrary program text, and masking it leaves an internal hostname, a
# username and an environment variable name intact, because all three match the boundary's
# word pattern. Only these frames license the host-message tier.
_SOURCE_HOST_MESSAGE_FRAMING = {
    SOURCE_CLAUDE_CODE: (
        r"^<tool_use_error>\s*",
        r"^Output does not match required schema:\s*",
    ),
}


def host_authored_framing(source: str) -> tuple[str, ...]:
    """The frames after which this host speaks for itself, empty when undeclared.

    The only framing that licenses reading a name out of what follows it.
    """
    return _SOURCE_HOST_MESSAGE_FRAMING.get(source, ())


def declared_failure_framing(source: str) -> tuple[str, ...]:
    """Every prefix by which this host declares a result to be a failure.

    A different question from either table alone, and it has to read both. "Did the host call
    this a failure" and "may a name be read out of it" are independent: a protocol message is
    a failure the host framed, and it licenses a read; a generic envelope is a failure the
    host framed and licenses nothing.

    Keeping them apart is what made the failure classifier and the operand extractor disagree:
    the protocol frames were added to one table only, so a ``<tool_use_error>`` result was not
    recognised as a failure at all and the tier that reads it could never be reached in
    production. Anything asking "is this a failure" reads this.
    """
    return generic_failure_framing(source) + host_authored_framing(source)


# What an envelope is decides whether the goal keeps it: the host's own words never are, a command block is.
KIND_AGENT_MESSAGE = "agent_message"
KIND_TASK_NOTIFICATION = "task_notification"
KIND_SYSTEM_REMINDER = "system_reminder"
KIND_COMMAND = "command"

_KINDS_NOT_IN_THE_GOAL = frozenset(
    {KIND_AGENT_MESSAGE, KIND_TASK_NOTIFICATION, KIND_SYSTEM_REMINDER}
)

# Long enough that a person's own sentence never opens it.
# The table repeats it as a literal; a test keeps them equal.
_PEER_CLOSING_OPENER = (
    "This came from another Claude session \u2014 not typed by your user"
)

# Host markup in the user's turn: kind, then (opener, closer, runs to end).
# A pure literal, because the parity guard reads it without importing.
_SOURCE_PROMPT_ENVELOPE_KINDS: dict[
    str, tuple[tuple[str, tuple[str, str, bool]], ...]
] = {
    SOURCE_CLAUDE_CODE: (
        (
            "agent_message",
            ("Another Claude session sent a message:", "\n</agent-message>", True),
        ),
        ("agent_message", ("<agent-message", "\n</agent-message>", True)),
        (
            "agent_message",
            (
                'That "other Claude session" is an agent',
                "permission laundering.",
                False,
            ),
        ),
        (
            "agent_message",
            (
                "Another Claude session sent a message:\n<cross-session-message",
                "\n</cross-session-message>",
                True,
            ),
        ),
        (
            "agent_message",
            ("<cross-session-message", "\n</cross-session-message>", True),
        ),
        (
            "agent_message",
            (
                "This came from another Claude session \u2014 not typed by your user",
                "permission laundering.",
                False,
            ),
        ),
        ("task_notification", ("<task-notification>", "</task-notification>", True)),
        ("system_reminder", ("<system-reminder>", "</system-reminder>", True)),
        ("agent_message", ("<agent-message>", "</agent-message>", True)),
        ("command", ("<command-name>", "</command-name>", True)),
        ("command", ("<command-message>", "</command-message>", True)),
        ("command", ("<command-args>", "</command-args>", True)),
        ("command", ("<local-command-caveat>", "</local-command-caveat>", True)),
        ("command", ("<local-command-stdout>", "</local-command-stdout>", True)),
    ),
}


def _declared(source: str) -> tuple[tuple[str, tuple[str, str, bool]], ...]:
    return _SOURCE_PROMPT_ENVELOPE_KINDS.get(source, ())


# Openers the host only ever writes at the start of the text or of a line.
_SOURCE_LINE_START_OPENERS: dict[str, frozenset[str]] = {
    SOURCE_CLAUDE_CODE: frozenset(
        {
            "Another Claude session sent a message:",
            "<agent-message",
            'That "other Claude session" is an agent',
            "Another Claude session sent a message:\n<cross-session-message",
            "<cross-session-message",
            _PEER_CLOSING_OPENER,
        }
    ),
}


def line_start_openers(source: str) -> frozenset[str]:
    """The declared openers that are markup only where a line begins, empty when undeclared.

    A subagent's report is a block the host writes on lines of its own. The same words in the
    middle of a sentence are a person mentioning the markup, and reading that as the host's would
    turn the rest of their prompt into host text.
    """
    return _SOURCE_LINE_START_OPENERS.get(source, frozenset())


def prompt_envelope(source: str) -> tuple[tuple[str, str, bool], ...]:
    """The machine markup this host wraps around text in the user's turn, empty when undeclared.

    Abstains like every other table here. An undeclared host is left to the boundary's own
    closed set rather than being told another host's markup, because a marker that is
    ordinary text on some other host would silently delete a user's words.

    A subagent's report arrives as a lead-in line, an ``<agent-message from="...">`` block and a
    closing paragraph. That paragraph ends at its own last words, so an instruction typed
    straight after a pasted report stays the person's. When those words are not found (a wrap can
    split them) it ends at the next blank line: none of its lines are promoted to the person's
    words, and what they typed after the blank line is kept. Its closer carries a leading newline because the host indents every line
    of the report: only a closing tag at the start of a line is the host's own, and one the
    report merely quotes sits on an indented line and does not end the wrapper.
    """
    return tuple(entry for _, entry in _declared(source))


def openers_kept_out_of_the_goal(source: str) -> tuple[str, ...]:
    """The declared openers whose envelopes are the host's own words, empty when undeclared.

    Derived from what each envelope is, so an envelope a host starts declaring cannot be
    recognised by the span cutter and still be kept in the goal for want of a second list.
    """
    return tuple(
        entry[0] for kind, entry in _declared(source) if kind in _KINDS_NOT_IN_THE_GOAL
    )


# Only a host that signals compaction can bound a no-repeat window, so others send no session.
_SOURCES_WITH_A_COMPACTION_SIGNAL = frozenset({SOURCE_CLAUDE_CODE})


def has_compaction_signal(source: str) -> bool:
    return source in _SOURCES_WITH_A_COMPACTION_SIGNAL


# Who the host says started a turn, by the value on the prompt's own transcript record.
_SOURCE_TURN_ORIGINS: dict[str, dict[str, bool]] = {
    SOURCE_CLAUDE_CODE: {
        "human": True,
        "sdk": True,
        "peer": False,
        "task_notification": False,
    },
}


def turn_origins(source: str) -> dict[str, bool]:
    """Each origin this host declares and whether it is a person, empty when undeclared.

    ``True`` is a person, or a program driving the harness, which is that customer's principal.
    ``False`` is the host or another agent. Measured over 14 days of Claude Code transcripts: 131
    ``human``, 340 ``sdk``, 145 ``peer`` (a subagent's report) and 200 ``task_notification``.
    """
    return _SOURCE_TURN_ORIGINS.get(source, {})


def is_turn_origin_a_principal(source: str, origin: str) -> bool | None:
    """Whether the host says a person started this turn, or ``None`` when it says nothing.

    Abstains on an undeclared host like every other table here. On a declared host an origin
    the table does not list is nobody: a new value is far more often a new kind of
    machine-started turn than a new kind of person, and reading one as a person lets machine
    text authorise a standing order.
    """
    origins = turn_origins(source)
    if not origins:
        return None
    return origins.get(origin, False)
