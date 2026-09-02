"""Which grammars license reading a name, and what they refuse to read it from.

The CPython fixtures are byte-exact output captured from a real interpreter. The V8 fixtures
are real ``node v26.0.0`` output kept deliberately after the anchor was withdrawn, because
what has to be pinned now is that none of it yields anything.

**Every negative fixture here co-locates adversarial text with a REAL grammar.** The previous
version removed the grammar entirely from each negative case, so it only ever proved that text
with no traceback in it yields nothing. That is the easy half, and it is why four separate
leaks survived a green suite: the shapes that leak are the ones where a genuine grammar and
untrusted text sit in the same result, which the Bash tool's combined stdout and stderr stream
makes routine rather than contrived.
"""

from __future__ import annotations

import pytest

from hyperstruck.ide.language_anchors import anchored_name

CPYTHON_PLAIN = """Traceback (most recent call last):
  File "/private/tmp/anch/plain.py", line 1, in <module>
    import nope_module_xyz
ModuleNotFoundError: No module named 'nope_module_xyz'"""

CPYTHON_CHAINED = """Traceback (most recent call last):
  File "/private/tmp/anch/chained.py", line 2, in <module>
    raise ValueError("inner")
ValueError: inner

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/private/tmp/anch/chained.py", line 4, in <module>
    raise RuntimeError("outer") from e
RuntimeError: outer"""

CPYTHON_SYNTAX = """Traceback (most recent call last):
  File "/private/tmp/anch/syn.py", line 1
    def ( {
        ^
SyntaxError: invalid syntax"""

V8_REFERENCE = """/private/tmp/anch/ref.js:1
notDefinedAnywhere();
^

ReferenceError: notDefinedAnywhere is not defined
    at Object.<anonymous> (/private/tmp/anch/ref.js:1:1)
    at Module._compile (node:internal/modules/cjs/loader:1829:14)"""

V8_ERROR_CODE = """node:internal/assert/utils:146
  throw error;
  ^

AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:

1 !== 2

    at Object.<anonymous> (/private/tmp/anch/ass.js:1:19)
    at Module._compile (node:internal/modules/cjs/loader:1829:14)"""

# The three classes this module's every previous rule shipped. Each appears below beside a
# real grammar, never alone.
LEAKS = [
    pytest.param("internal.corp.example.com", id="an_internal_host"),
    pytest.param("tlynch", id="a_username"),
    pytest.param("DATABASE_PASSWORD_PROD", id="an_env_var_name"),
]


def name_of(text: str) -> str | None:
    return anchored_name([line for line in text.splitlines() if line.strip()])


class TestACPythonBlockNamesItsOwnFailure:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (CPYTHON_PLAIN, "ModuleNotFoundError"),
            (CPYTHON_SYNTAX, "SyntaxError"),
        ],
        ids=["plain", "syntax_error"],
    )
    def test_the_class_name_is_read_and_never_the_message(
        self, text: str, expected: str
    ) -> None:
        """``KeyError: 'secret-tenant-id'`` yields ``KeyError``. That is what makes the tier
        safe without claiming the interpreter authored the text."""
        assert name_of(text) == expected

    def test_a_chained_exception_reads_the_block_that_stopped_the_program(self) -> None:
        """``raise X from Y`` prints the handling exception last, and that is the one that
        actually stopped the program. Reading the first block would gate on the cause."""
        assert name_of(CPYTHON_CHAINED) == "RuntimeError"


class TestTheBlockIsWhatIsRead:
    """The leak that a green suite hid: the read must be bounded by the licensed block.

    An earlier rule collected every frame line anywhere in the window and read below the last
    one, so any indented ``File "`` text appearing after a traceback moved the anchor out of
    the block and handed the read to whatever followed it.
    """

    @pytest.mark.parametrize("leak", LEAKS)
    def test_text_after_the_block_cannot_become_the_name(self, leak: str) -> None:
        """A genuine traceback, then unrelated indented output, then a leak class. The real
        exception must win, and this must never be the trailing line."""
        text = (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 1, in <module>\n'
            "    boom()\n"
            "ValueError: boom\n"
            "Checking inputs:\n"
            '  File "notes.txt" is missing\n'
            f"{leak}: unreachable"
        )

        assert name_of(text) == "ValueError"

    @pytest.mark.parametrize("leak", LEAKS)
    def test_a_run_of_elisions_is_not_a_stack(self, leak: str) -> None:
        """``...`` is CPython's elided-frame marker and indents like a frame, so a run made
        only of them would otherwise satisfy the licence and hand over the next line."""
        assert name_of(f"Traceback (most recent call last):\n  ...\n{leak}: down") is None

    @pytest.mark.parametrize("leak", LEAKS)
    def test_a_banner_below_the_frames_licenses_nothing(self, leak: str) -> None:
        """A result that merely contains the banner string somewhere, a grep hit or a cat of
        a fixture, must not license a read of a region above it."""
        text = f'  File "x", line 1\n{leak}: permission denied\nTraceback (most recent call last):'

        assert name_of(text) is None


class TestAdversarialTextBesideARealGrammar:
    """The shapes a combined stdout and stderr stream makes routine."""

    @pytest.mark.parametrize("leak", LEAKS)
    def test_a_leak_class_above_a_real_traceback_is_not_read(self, leak: str) -> None:
        text = (
            f"{leak}: permission denied\n"
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 1, in <module>\n'
            "    boom()\n"
            "KeyError: 'k'"
        )

        assert name_of(text) == "KeyError"

    @pytest.mark.parametrize("leak", LEAKS)
    def test_a_leak_class_inside_the_frame_run_is_not_read(self, leak: str) -> None:
        """Indented text inside the run is a source echo and is never the exception line."""
        text = (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 1, in <module>\n'
            f"    print('{leak}')\n"
            "KeyError: 'k'"
        )

        assert name_of(text) == "KeyError"


class TestV8IsWithdrawnAndYieldsNothing:
    """V8's published format has no banner, so nothing can license a read of it.

    The anchor was declared, executed against the real client, and found to return all three
    leak classes: its only licence was an indented ``at `` line somewhere below, which a Java
    stack trace also satisfies, and the line above a frame is as likely to be a username as an
    error name. These fixtures are real ``node`` output and are kept so that re-declaring the
    anchor without a banner turns them red rather than green.
    """

    @pytest.mark.parametrize(
        "text", [V8_REFERENCE, V8_ERROR_CODE], ids=["reference_error", "error_code_shape"]
    )
    def test_real_node_output_yields_nothing(self, text: str) -> None:
        assert name_of(text) is None

    @pytest.mark.parametrize("leak", LEAKS)
    def test_an_at_frame_licenses_nothing_above_it(self, leak: str) -> None:
        assert name_of(f"{leak}: permission denied\n    at Object.<anonymous> (/a.js:3:9)") is None

    def test_a_java_stack_trace_licenses_nothing_either(self) -> None:
        """``\\tat com.acme.Foo.bar(Foo.java:10)`` matches the same frame shape V8 uses, which
        is the clearest statement of why that shape is not a licence."""
        assert name_of("myapp.prod.internal: starting\n\tat com.acme.Foo.bar(Foo.java:10)") is None


class TestNothingIsReadWithoutTheGrammarThatLicensesIt:
    def test_a_bare_name_and_message_is_not_a_traceback(self) -> None:
        assert name_of("ModuleNotFoundError: No module named 'missing'") is None

    def test_a_banner_with_no_frames_licenses_nothing(self) -> None:
        assert name_of("Traceback (most recent call last):\nValueError: inner") is None

    def test_frames_with_no_banner_license_nothing(self) -> None:
        """Frame-shaped indented text appears in ordinary program output, so the frames alone
        are not enough. The banner is CPython's published licence line."""
        assert name_of('  File "/app/x.py", line 1, in <module>\nValueError: inner') is None

    def test_a_block_that_never_ends_yields_nothing(self) -> None:
        """A truncated traceback has no unindented line to read, and must abstain rather than
        run off the end of the window."""
        assert name_of('Traceback (most recent call last):\n  File "/app/x.py", line 1') is None

    @pytest.mark.parametrize(
        "output",
        [
            "fetching\ninternal.corp.example.com",
            "tlynch: permission denied",
            "root:*:0:0:System:/root:/bin/sh",
        ],
    )
    def test_a_programs_own_output_names_no_author(self, output: str) -> None:
        assert name_of(output) is None
