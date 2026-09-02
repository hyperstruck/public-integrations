"""What the packaged skills run when Claude Code loads them, and the recall command the model runs.

Claude Code runs every ```` ```! ```` block and inline ``!`command``` in a skill when it loads,
after pasting the skill arguments over ``$ARGUMENTS`` as plain text. Pasted text can always end
whatever quoting surrounds it, and a command that exits non-zero aborts the whole load. So the
hyper-learning recall is an example the model runs with a goal it quotes itself.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hyperstruck.ide import hook

_SKILLS = Path(hook.__file__).parent / "skills"
_HYPER_LEARNING = _SKILLS / "hyper-learning" / "SKILL.md"

_needs_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="the recall example is bash"
)


def _load_time_commands(skill: Path) -> list[str]:
    """Every command Claude Code would run when the skill loads, over-approximated.

    A fence may be indented, carry trailing spaces or start its command on the opening
    line, and an inline command may span lines.
    """
    text = skill.read_text()
    fenced = re.findall(r"`{3,}!(.*?)`{3,}", text, re.S)
    inline = re.findall(r"(?:^|(?<=\s))!`([^`]+)`", text, re.M)
    return fenced + inline


def _recall_example() -> str:
    blocks = re.findall(
        r"^```bash\n(.*?)^```$", _HYPER_LEARNING.read_text(), re.S | re.M
    )
    (block,) = [b for b in blocks if "--goal '<goal>'" in b]
    return block


def _hook_stub(label: str) -> str:
    """Reads stdin to the end like the real hook, then echoes the goal it was given."""
    return f"""#!/bin/sh
cat >/dev/null
while [ $# -gt 0 ]; do
  [ "$1" = --goal ] && printf '{label} goal=[%s]\\n' "$2"
  shift
done
"""


def _stub(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def _run_recall(
    tmp_path: Path, *, venv: bool = True, stdin_open: bool = False
) -> tuple[int, str]:
    """Run the recall example for the goal ``do x`` with stub hooks in the venv and on PATH.

    Output goes to a file, not a pipe, so a run killed on timeout cannot leave
    ``subprocess.run`` waiting on a pipe the stub still holds.
    """
    home = tmp_path / "home"
    home.mkdir()
    if venv:
        _stub(home / ".hyperstruck" / "venv" / "bin" / "python", _hook_stub("venv"))
    _stub(tmp_path / "bin" / "python3", _hook_stub("python3"))
    env = {"HOME": str(home), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin"}
    command = _recall_example().replace("'<goal>'", "'do x'")
    read_end, write_end = os.pipe()
    out = tmp_path / "out.txt"
    try:
        with out.open("w") as sink:
            result = subprocess.run(
                ["bash", "-c", command],
                stdin=read_end if stdin_open else subprocess.DEVNULL,
                stdout=sink,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=10,
                check=False,
            )
    finally:
        os.close(write_end)
        os.close(read_end)
    return result.returncode, out.read_text()


@pytest.mark.parametrize(
    ("snippet", "runs"),
    [
        ("```!\necho x\n```\n", True),
        ("  ```!\n  echo x\n  ```\n", True),
        ("```!   \necho x\n```   \n", True),
        ("```!echo x\n```\n", True),
        ("say !`echo a\necho b` now\n", True),
        ("~~~!\necho x\n~~~\n", False),
        ("```bash\necho x\n```\n", False),
    ],
)
def test_load_time_command_finder_covers_the_forms_claude_code_runs(
    tmp_path, snippet, runs
) -> None:
    """Claude Code 2.1.309 ran each True form when a probe skill loaded, and skipped ``~~~!``."""
    skill = tmp_path / "SKILL.md"
    skill.write_text(snippet)

    assert bool(_load_time_commands(skill)) is runs


def test_no_load_time_command_pastes_in_the_skill_arguments() -> None:
    """hyper-install still runs ``python -m hyperstruck.ide.install $ARGUMENTS`` when it loads.

    The set is compared exactly, so fixing hyper-install fails this test until its name is
    removed here.
    """
    offenders = {
        skill.parent.name
        for skill in _SKILLS.glob("*/SKILL.md")
        if any(re.search(r"\$ARGUMENTS|\$\d", c) for c in _load_time_commands(skill))
    }

    assert offenders == {"hyper-install"}


def test_hyper_learning_runs_nothing_when_it_loads() -> None:
    """Its distill examples carry placeholder text that would reach /distill on every load."""
    assert _load_time_commands(_HYPER_LEARNING) == []


def test_every_hook_call_in_hyper_learning_prefers_the_venv() -> None:
    """Bare ``python3`` often lacks the package, so each hook call runs ``"$HYPER_PY"``.

    Every bash block or prose line with a call first sets it with the recall example's two
    lines, which the runs below exercise.
    """
    text = _HYPER_LEARNING.read_text()
    fence = re.compile(r"^```bash\n.*?^```$", re.S | re.M)
    units = fence.findall(text) + fence.sub("", text).splitlines()
    runner = re.compile(r"(\S+)\s+-m\s+hyperstruck\.ide\.hook\b")
    calls = [(u, runs) for u in units if (runs := list(runner.finditer(u)))]

    assert len(calls) >= 5
    for unit, runs in calls:
        assert {run.group(1) for run in runs} == {'"$HYPER_PY"'}, unit
        venv_at = unit.find('HYPER_PY="$HOME/.hyperstruck/venv/bin/python"')
        fallback_at = unit.find('[ -x "$HYPER_PY" ] || HYPER_PY=python3')
        assert 0 <= venv_at < fallback_at < runs[0].start(), unit


@_needs_bash
def test_recall_example_runs_the_venv_hook(tmp_path) -> None:
    assert _run_recall(tmp_path) == (0, "venv goal=[do x]\n")


@_needs_bash
def test_recall_example_falls_back_to_python3_without_the_venv(tmp_path) -> None:
    assert _run_recall(tmp_path, venv=False) == (0, "python3 goal=[do x]\n")


@_needs_bash
def test_recall_example_does_not_wait_on_an_open_stdin(tmp_path) -> None:
    assert _run_recall(tmp_path, stdin_open=True) == (0, "venv goal=[do x]\n")
