from enum import Enum


class ResolvePurpose(str, Enum):
    """Why a learning resolve is being performed."""

    AGENT_LOOP = "agent_loop"
    EXPLICIT_RECALL = "explicit_recall"
