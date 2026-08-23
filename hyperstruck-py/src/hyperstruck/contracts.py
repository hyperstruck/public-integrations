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
from functools import lru_cache
from pathlib import Path

# Every entry is a small file shipped inside the wheel, so it cannot change under a running
# process and re-reading it per turn buys nothing. It was being opened and parsed on the
# recall and finalise paths, several times per turn.
_CACHE_SIZE = 8


@lru_cache(maxsize=_CACHE_SIZE)
def published_names(path: Path, key: str) -> frozenset[str]:
    """The names one contract publishes, or an empty set when it cannot be read.

    Degrades rather than raises, because these are read on the paths that finalise a turn.
    A missing or corrupt file is a packaging fault, and taking the whole episode down with
    it would turn one unreadable diagnostic into lost learning with nothing to see: the hook
    fails open by contract, so the exception would surface nowhere at all.

    Empty is the safe degradation in both directions by construction. Every caller asks
    "may I send this value", so an empty answer withholds the value and keeps the behaviour
    the client had before that value existed.

    The shape is checked rather than trusted, because the degradation is only safe when a
    bad contract yields *empty*. A JSON string passes ``frozenset`` and yields its
    characters: ``{"names": "error_type"}`` becomes ``{'r', '_', 'e', 'p', 'y', 't', 'o'}``,
    which is non-empty and matches nothing a caller will ever ask about, so the empty-means-
    unknown escape hatch never fires and every value is silently withheld instead.
    """
    try:
        names = json.loads(path.read_text())[key]
    except (OSError, ValueError, KeyError, TypeError):
        return frozenset()
    if not isinstance(names, (list, tuple)):
        return frozenset()
    return frozenset(name for name in names if isinstance(name, str))
