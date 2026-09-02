from enum import Enum


class InsightEventKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    RUN_STARTED = "run_started"
    PLANNING = "planning"
    PLANNED = "planned"
    RECALLING = "recalling"
    RECALLED = "recalled"
    ASKING = "asking"
    ANSWERED = "answered"
    AGENT_FAILED = "agent_failed"
    SYNTHESIZING = "synthesizing"
    FINDING = "finding"
    FINDING_SUPPRESSED = "finding_suppressed"
    RUN_FINISHED = "run_finished"
    RUN_FAILED = "run_failed"
