"""What each host's terminal statuses mean, declared by the host that emits them.

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
