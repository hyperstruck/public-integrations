"""A search of a hosted agent's claims, typed as the platform publishes it.

A search is a read: the claims nearest the question, written out as ``text`` by code,
with the same claims beside it as ``claims``. Nothing is stored or billed, so searching
again is always safe.
"""

from __future__ import annotations

from typing import Literal, TypedDict

ClaimSearchDetail = Literal["concise", "cited", "full"]
ClaimSearchShape = Literal["point", "as_of", "since", "set", "absent"]
ClaimSearchState = Literal[
    "settled", "unanswered", "conflicting", "open", "done", "ended"
]
ClaimSearchKind = Literal["value", "reading", "obligation", "event", "view", "relation"]


class ClaimSearch(TypedDict):
    """One search result. ``claims`` are the platform's Claim items, one per key the
    text renders."""

    as_of: str
    computed_at: str
    shape: ClaimSearchShape
    text: str
    claims: list[dict[str, object]]
    # Set when the result came from a narrower read than usual, saying why.
    degraded: str | None
    # A filtered set's next page cursor; null on the last page and on every other shape.
    cursor: str | None
    # True when no claim shares a word with the question, so the claims are the nearest by meaning alone.
    shares_no_word: bool
    # How many more claims the question's words matched than the result hands over.
    more_matched: int
