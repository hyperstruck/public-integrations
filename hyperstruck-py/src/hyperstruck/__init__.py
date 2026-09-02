"""Hyperstruck: learning for your agents.

Plug a middleware into your agent and it gets sharper run over run. The learning
runs on the Hyperstruck platform; this package is a thin, swappable client.

Quick start (LangGraph)::

    from hyperstruck.langgraph import HyperstruckLearningMiddleware

    agent = create_agent(
        model,
        tools=tools,
        middleware=[HyperstruckLearningMiddleware(api_key=..., agent_name="support-bot")],
    )

The framework-neutral pieces (the client, identity, and wire types) live at the
top level so other framework adapters can reuse them.
"""

from __future__ import annotations

from hyperstruck._version import __version__
from hyperstruck._wire import Episode, ResolvedContext, StepRecord, TerminalOutcome, ToolSpec
from hyperstruck.client import HostedLearningClient, LearningClient
from hyperstruck.identity import AgentIdentity

__all__ = [
    "AgentIdentity",
    "Episode",
    "HostedLearningClient",
    "LearningClient",
    "ResolvedContext",
    "StepRecord",
    "TerminalOutcome",
    "ToolSpec",
    "__version__",
]
