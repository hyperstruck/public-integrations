from enum import Enum


class CitationAbsence(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AMBIGUOUS_MATCH = "ambiguous_match"
    SOURCE_UNDECLARED = "source_undeclared"
    NO_PASSAGE_LANE = "no_passage_lane"
    PREDATES_CITATIONS = "predates_citations"
    CITATION_WRITE_LOST = "citation_write_lost"
