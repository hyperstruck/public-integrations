"""Measure what the gate-operand rule actually derives, against real local failures.

Run this before changing anything in ``ide/failure_template.py`` or the framing table, and
again afterwards. A unit test cannot answer what this answers: every fixture is a shape
someone thought of, and the shapes that matter are the ones real results actually take.
Measured against a real corpus, an extraction rule that looks well covered by its tests can
derive an operand on none of them.

It calls the real ``gate_bearing_result`` rather than reimplementing it, so it stays honest
across any change to the extraction rule, and it forces both release switches on so the
figures describe the rule rather than the current posture.

Read the identifier-match report as an aid, not as a safety result. ``self_identifiers`` knows only
this machine's own names, so a third party's hostname or an unset environment variable is
invisible to it, and a clean report is the absence of evidence rather than evidence of
absence.

Local only. It reads this machine's own transcripts, keeps nothing but aggregate counts and
the distinct operand list, and writes no file unless asked. It is not part of the published
package.

    python3.13 dev/measure_gate_operands.py
    python3.13 dev/measure_gate_operands.py --census operands.json
"""

from __future__ import annotations

import argparse
import collections
import getpass
import json
import os
import pathlib
import socket
import sys

# requires-python already declares 3.11, but that declaration binds an installer. This is
# run straight off a checkout, where the macOS system python3 is 3.9 and the failure is an
# ImportError from deep inside the package.
if sys.version_info < (3, 11):  # noqa: UP036
    raise SystemExit(
        f"hyperstruck needs Python 3.11+, and this is {sys.version.split()[0]}. The system "
        f"python3 on macOS is 3.9, so run this with an explicit interpreter, e.g. python3.13."
    )

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from hyperstruck.ide import hook, step_result
from hyperstruck.ide.host_vocabularies import SOURCE_CLAUDE_CODE

# The recurrence floor the boundary enforces before an operand may be frozen onto a rule at
# all. Counting occurrences here OVERSTATES what clears it: Core counts distinct runs, and
# one session re-running a failing command emits the same signature many times, so a value
# that looks like five here can be one run. Read the figure below as an upper bound on what
# would clear the floor, never as a floor. Distinct runs are not recoverable from a
# transcript, which is why this counts what it can and says which direction it errs in.
SUPPORT_FLOOR = 5


def self_identifiers() -> dict[str, str]:
    """This operator's own identifiers, each mapped to what it is, so a hit can be judged.

    The character markers this replaces ("/", "@", "\\") could not detect a single one of
    the three classes the rule was shipping: ``internal.corp.example.com``, ``tlynch`` and
    ``DATABASE_PASSWORD_PROD`` carry none of them, so the census reported zero suspects
    while all three were live. Asking the machine what its own names are finds them by
    construction rather than by guessing at their spelling.

    Each entry carries *why* it is here, because the set necessarily includes generic names
    (``PATH``, ``HOME``, a hostname label like ``local``) that are perfectly good operands.
    An unexplained ``LEAK`` line next to those is what teaches an operator to skim.

    Bounded by what this machine knows, and the bound runs the wrong way for comfort: a
    third party's hostname is invisible to it, and a variable that failed *because it was
    unset* is by definition absent from ``os.environ``. Two of the three classes it is named
    for can therefore go undetected. A clean report is the absence of evidence, never
    evidence of absence.
    """
    found: dict[str, str] = {}
    try:
        found[getpass.getuser()] = "this machine's username"
    except (OSError, KeyError):
        # No passwd entry for this uid, which is normal in a container or on some CI
        # runners. Losing one class of detection is not a reason to lose the whole report.
        pass
    host = socket.gethostname()
    if host:
        found.setdefault(host, "this machine's hostname")
        for label in host.split("."):
            if label:
                found.setdefault(label, f"a label of this machine's hostname {host!r}")
    for name in os.environ:
        found.setdefault(name, "an environment variable name set here")
    return found


def transcripts(root: pathlib.Path):
    for path in root.rglob("*.jsonl"):
        try:
            yield path.read_text(errors="replace").splitlines()
        except OSError:
            continue


def failures(root: pathlib.Path) -> list[str]:
    """Every tool result this host declared a failure, by its own ``is_error`` flag."""
    found = []
    for lines in transcripts(root):
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("type") != "user":
                continue
            blocks = (record.get("message") or {}).get("content")
            if not isinstance(blocks, list):
                continue
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                if not block.get("is_error"):
                    continue
                content = block.get("content")
                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    )
                if isinstance(content, str) and content.strip():
                    found.append(content)
    return found


def _share(part: int, whole: int) -> str:
    """``part`` as a percentage of ``whole``, saying so when there is no denominator.

    ``whole`` is the population the client actually reaches, and it is zero in exactly the
    state this script exists to make visible: a classifier that agrees with production on
    nothing. Crashing there would report that state as a broken instrument.
    """
    if whole <= 0:
        return "no denominator"
    return f"{part / whole:.1%}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=pathlib.Path, default=None)
    parser.add_argument(
        "--transcripts",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".claude/projects",
    )
    args = parser.parse_args()

    if not args.transcripts.is_dir():
        print(f"no transcripts at {args.transcripts}", file=sys.stderr)
        return 1

    # The support floor answers "may the boundary be sent one", which is a release question
    # about the deployed contract rather than about this rule, so it is forced on.
    #
    # The authorship anchor is NOT forced, and that is the change the tiering makes to this
    # script. It used to be, because every path abstained and leaving it alone made every
    # figure zero by construction. It is now the rule under measurement: forcing it would
    # measure what the extraction *could* derive if provenance were ignored, which is the
    # number that made a positional rule look safe on this same corpus while it returned a
    # hostname, a username and an environment variable name.
    step_result.is_operand_admitted_on_support = lambda: True

    corpus = failures(args.transcripts)
    if not corpus:
        print("no host-declared failures found", file=sys.stderr)
        return 1

    # Both provenances, because they run different rules and only one of them was ever
    # measured. The framed branch is what a Claude Code result reaches; the labelled branch
    # is what a host putting its message in ``stderr`` reaches, and a corpus from one host
    # can never exercise the other. Reading the same text through both is what makes the
    # labelled rule visible to a machine that has only Claude Code transcripts on it.
    census: collections.Counter[str] = collections.Counter()
    labelled_census: collections.Counter[str] = collections.Counter()
    # Whether the CLIENT's own classifier agrees with the host that these are failures, given
    # only what a PostToolUse payload carries. It has to be reported rather than assumed: the
    # protocol frames were once declared in a table the classifier did not read, so every
    # tier-1 shape was counted here while production would have skipped it as a success. A
    # figure below 100% means this measurement is describing a population the client cannot
    # reach, and the operand rate above it is inflated by exactly that much.
    client_agrees = 0
    for text in corpus:
        # Everything below is measured over the population PRODUCTION reaches, not over every
        # host-declared failure. A result the client does not classify as a failure never
        # reaches gate_bearing_result at all, so counting it would report a rate no real run
        # can produce.
        if not hook._is_error({"tool_response": text}, SOURCE_CLAUDE_CODE):
            continue
        client_agrees += 1
        framed = step_result.gate_bearing_result(
            {"tool_response": text}, is_error=True, source=SOURCE_CLAUDE_CODE
        )
        if framed:
            census[framed[step_result.GATE_FIELD]] += 1
        # The whole field, not its first line. That slice was correct while the labelled
        # rule abstained above one line; under the tiering a labelled field reaches the
        # language tier, whose grammars need the frames and the banner, so a first-line
        # slice would make this pass derive nothing by construction and read as a result.
        labelled = step_result.gate_bearing_result(
            {"stderr": text}, is_error=True, source=SOURCE_CLAUDE_CODE
        )
        if labelled:
            labelled_census[labelled[step_result.GATE_FIELD]] += 1

    total = client_agrees
    derived_count = sum(census.values())
    clearing = {value for value, n in census.items() if n >= SUPPORT_FLOOR}
    usable = sum(n for value, n in census.items() if value in clearing)
    singletons = sum(1 for n in census.values() if n == 1)

    print(f"host-declared failures   {len(corpus)}")
    print(
        f"reachable in production   {client_agrees}"
        f" ({_share(client_agrees, len(corpus))} of them)"
        "  <- every figure below is over THIS population, not the line above"
    )
    print(f"operand derived          {derived_count} ({_share(derived_count, total)})")
    print(f"distinct operands        {len(census)}")
    print(f"singletons               {singletons}")
    print(
        f"reach {SUPPORT_FLOOR} occurrences    {len(clearing)}  (upper bound on clearing the floor)"
    )
    print(f"USABLE coverage (upper)  {usable} ({_share(usable, total)})")

    print(
        f"labelled-branch operands {sum(labelled_census.values())}"
        f"  ({len(labelled_census)} distinct, each corpus text's first line as a stderr field)"
    )

    mine = self_identifiers()
    matched = sorted({v for v in (*census, *labelled_census) if v in mine})
    # "MATCH", not "LEAK". Membership is a prompt to look, not a verdict: the set holds
    # generic names (PATH, a hostname label) that are perfectly good operands, and it misses
    # a remote hostname and an unset variable entirely.
    print(f"\noperands matching one of this machine's own identifiers: {len(matched)}")
    for value in matched:
        print(f"  MATCH  {value!r}  ({mine[value]})")
    if not mine:
        print("  (no identifiers could be read here, so this check ran on nothing)")

    print(f"\noperands clearing the floor ({len(clearing)}):")
    for value, count in census.most_common():
        if value in clearing:
            print(f"{count:6d}  {value!r}")

    print(
        f"\nall {len(census)} distinct framed operands follow; read them, do not skim:"
    )
    for value, count in census.most_common():
        print(f"{count:6d}  {value!r}")

    # Listed, not just counted. Exact matching above catches at most one of the three leak
    # classes, so reading the values is the only backstop, and the branch that was invisible
    # until this script grew a second pass is the one that most needs reading.
    print(f"\nall {len(labelled_census)} distinct labelled operands follow:")
    for value, count in labelled_census.most_common():
        print(f"{count:6d}  {value!r}")

    if args.census:
        args.census.write_text(
            json.dumps(
                {
                    "framed": census.most_common(),
                    "labelled": labelled_census.most_common(),
                },
                indent=1,
            )
        )
        print(f"\ncensus written to {args.census}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
