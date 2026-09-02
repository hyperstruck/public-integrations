"""A hosted answer at a chosen level of detail, and the same answer later with more.

The answer is model-written, so it is fetched again rather than asked again: ``more`` reads the
stored answer at a higher level, word for word, and bills nothing. Each level's body is typed as
the one below it plus what it adds, so a type checker knows which sections a response carries.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypedDict, TypeVar, cast, overload

AnswerDetail = Literal["answer", "findings", "claims", "everything"]


FlagKind = Literal["number", "name", "status", "relation", "invented"]
FlagSource = Literal["model", "code"]


class SupportFlag(TypedDict):
    """One error a check found: ``words`` carry it and ``correction`` is what the evidence states.

    ``is_corrected`` is true when code already put the correction into the text.
    """

    kind: FlagKind
    words: str
    correction: str
    source: FlagSource
    finding_id: str | None
    is_corrected: bool


class BulletSupport(TypedDict):
    """A verdict on one lead, bullet or finding. ``flags`` lists every error the check found."""

    verdict: Literal["supported", "partly_supported", "unsupported", "unchecked"]
    unsupported_part: str | None
    span: list[int] | None
    flags: list[SupportFlag]


class AnswerLead(TypedDict):
    """The opening paragraph as a field, from the ``findings`` level up.

    The key is absent below that level and null when the answer has no lead, so read it with ``get``.

    ``finding_ids`` and ``reference_ids`` are what the writer cited, not what the check judged
    against. ``is_rewritten`` is true when the check flagged the writer's lead and this is its rewrite.
    """

    text: str
    finding_ids: list[str]
    reference_ids: list[int]
    support: BulletSupport
    has_unreadable_source: bool
    rests_on_held: bool
    is_rewritten: bool


class AnswerBody(TypedDict):
    """The default level: the answer, its references and the documents they cite."""

    agent_id: str
    detail: AnswerDetail
    answer_id: str
    question: str
    as_of: str
    version: str | None
    answer: str | None
    answer_unavailable_reason: str | None
    # False when the writer failed and code laid out the findings; null when no writer ran.
    is_written: bool | None
    # Null wherever the step producing a section did not run; empty when it ran and found nothing.
    references: list[dict[str, object]] | None
    documents: dict[str, dict[str, object]]
    completeness: dict[str, object] | None
    silence: list[dict[str, object]]
    more: dict[str, str] | None
    more_unavailable_reason: str | None


class FindingsBody(AnswerBody):
    # Absent at the answer level, so read it from a findings body; null when the answer has no lead.
    lead: AnswerLead | None
    findings: list[dict[str, object]] | None
    sections: list[dict[str, object]] | None
    results: list[dict[str, object]] | None
    appended_finding_ids: list[str] | None
    background_finding_ids: list[str] | None
    interpretation: dict[str, object] | None
    subject: list[dict[str, object]] | None
    selection: dict[str, object] | None
    multi_valued_slots: list[dict[str, object]] | None
    boundary: dict[str, object] | None
    change: dict[str, object] | None
    obligations: dict[str, object] | None


class ClaimsBody(FindingsBody):
    claims: dict[str, dict[str, object]] | None


class EverythingBody(ClaimsBody):
    read_documents: list[dict[str, object]] | None
    sources: dict[str, object] | None
    stage_events: list[dict[str, object]] | None


BodyT = TypeVar("BodyT", bound=AnswerBody)


@dataclass(frozen=True)
class Answer(Generic[BodyT]):
    """One answer at one level: ``body`` is the response, and ``more`` fetches a higher level."""

    body: BodyT
    _fetch: Callable[[str], Awaitable[dict[str, Any]]] = field(
        repr=False, compare=False
    )

    @overload
    async def more(self, detail: Literal["findings"]) -> Answer[FindingsBody]: ...
    @overload
    async def more(self, detail: Literal["claims"]) -> Answer[ClaimsBody]: ...
    @overload
    async def more(self, detail: Literal["everything"]) -> Answer[EverythingBody]: ...
    async def more(self, detail: AnswerDetail) -> Answer[Any]:
        """This same answer at ``detail``, read from where the response says it is served."""
        links = self.body.get("more")
        if links is None:
            reason = self.body.get("more_unavailable_reason") or "unknown"
            raise ValueError(f"this answer has no more detail to fetch: {reason}")
        if detail not in links:
            raise ValueError(
                f"{detail!r} is not above this answer's level {self.body.get('detail')!r}"
            )
        return Answer(cast(Any, await self._fetch(links[detail])), self._fetch)
