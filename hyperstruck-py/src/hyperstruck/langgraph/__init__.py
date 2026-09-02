"""LangGraph host for Hyperstruck learning.

The first framework adapter: a LangChain v1 / LangGraph ``AgentMiddleware`` that
runs the full learning loop against the platform. Requires the ``langgraph``
extra (``pip install hyperstruck[langgraph]``).
"""

from __future__ import annotations

from hyperstruck.langgraph.middleware import (
    HyperstruckLearningMiddleware,
    assert_innermost,
)

__all__ = ["HyperstruckLearningMiddleware", "assert_innermost"]
