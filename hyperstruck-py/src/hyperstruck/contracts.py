"""Values a receiving side publishes, mirrored here rather than assumed.

Three boundary fields are closed sets validated behind ``extra="forbid"``: the step
result names a gate derives from, the decline reasons, and the recall outcomes. A name
this client sends and the deployed boundary cannot parse is not a degraded diagnostic,
it costs the run its whole episode, and this client reaches a user's machine on a
different schedule from the API it talks to.

So each set is vendored as a JSON artefact read at use, never as a constant in code and
never as an import: the SDK asserts that no engine module loads, so a shared contract has
to cross as data both sides can read. Adding a member is then a boundary change followed
by a one-line edit here, in that order, and a client running ahead of its API degrades
rather than losing what it was trying to report.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from hyperstruck.debug import debug as _debug

# Every entry is a small file shipped inside the wheel, so it cannot change under a running
# process and re-reading it per turn buys nothing. It was being opened and parsed on the
# recall and finalise paths, several times per turn.
_CACHE_SIZE = 8


@lru_cache(maxsize=_CACHE_SIZE)
def _published(path: Path) -> Mapping[str, object]:
    """One parse of one contract file, shared by every accessor below.

    Each accessor used to read and parse the file itself, so a contract consulted for three
    keys was opened and parsed three times. That is free in a long-lived process and is not
    here: this client runs as a short-lived subprocess per tool call, so the cache never warms
    and every parse is paid on every call.

    Degrades to empty rather than raising, because these are read on the paths that finalise a
    turn. A missing or corrupt file is a packaging fault, and taking the episode down with it
    would turn one unreadable diagnostic into lost learning with nothing to see: the hook
    fails open by contract, so the exception would surface nowhere at all.
    """
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        _debug(f"contract at {path.name} is unreadable ({type(exc).__name__}), degrading to empty")
        return {}
    if not isinstance(loaded, dict):
        _debug(f"contract at {path.name} is not an object, degrading to empty")
        return {}
    return loaded


def published_names(path: Path, key: str) -> frozenset[str]:
    """The names one contract publishes, or an empty set when it cannot be read.

    Empty is the safe degradation in both directions by construction. Every caller asks "may I
    send this value", so an empty answer withholds the value and keeps the behaviour the client
    had before that value existed.

    The shape is checked rather than trusted, because the degradation is only safe when a bad
    contract yields *empty*. A JSON string passes ``frozenset`` and yields its characters, so
    ``{"names": "error_type"}`` becomes a non-empty set matching nothing a caller will ever ask
    about, and the empty-means-unknown escape hatch never fires.
    """
    names = _published(path).get(key)
    if not isinstance(names, (list, tuple)):
        return frozenset()
    return frozenset(name for name in names if isinstance(name, str))


def published_shape(path: Path, key: str) -> Mapping[str, object]:
    """The scalar constraints one contract publishes, or empty when it cannot be read.

    Empty makes the caller withhold, which matters more here than for names: a caller that
    read a missing bound as "no bound" would turn a packaging fault into the leak the bound
    exists to prevent.

    Non-scalar members are dropped rather than passed through, because a caller compiling a
    pattern or comparing a length against a nested object raises inside a hook that fails open,
    which surfaces the fault nowhere at all.
    """
    shape = _published(path).get(key)
    if not isinstance(shape, dict):
        return {}
    return {
        name: value
        for name, value in shape.items()
        if isinstance(name, str) and isinstance(value, (str, int, float, bool))
    }
