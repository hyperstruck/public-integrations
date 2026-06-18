"""Quickstart: add Hyperstruck learning to a LangGraph agent.

Install:
    pip install hyperstruck[langgraph]

Run:
    export HYPERSTRUCK_API_KEY=hsk_...      # from the Hyperstruck dashboard
    export OPENAI_API_KEY=...               # your model provider, as usual
    python quickstart_langgraph.py

What it shows: the entire integration is three lines (construct the middleware,
register it). The agent then gets sharper run over run. There is no memory code,
no episode assembly, and no engine import: the learning runs on the platform.
"""

from __future__ import annotations

import asyncio

from langchain.agents import create_agent
from langchain.tools import tool

from hyperstruck.langgraph import HyperstruckLearningMiddleware


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order's status by id."""
    return f"Order {order_id}: shipped, arriving tomorrow."


async def main() -> None:
    # The whole integration: one middleware, an API key, and your agent's id.
    learning = HyperstruckLearningMiddleware(
        # api_key defaults to $HYPERSTRUCK_API_KEY
        agent_id="support-bot",
        # Declare sensitive tool fields so they are redacted before they ever
        # leave your environment (optional).
        tool_sensitivity={"lookup_order": {}},
    )

    agent = create_agent(
        "openai:gpt-4o-mini",
        tools=[lookup_order],
        middleware=[learning],
    )

    result = await agent.ainvoke({"messages": [("user", "Where is order 1234?")]})
    print(result["messages"][-1].content)

    # The run was observed and the learnings it used were reinforced in the
    # background. Inspect the middleware's counters for visibility.
    print(
        f"learnings injected: {learning.stats.learnings_injected}, "
        f"tool calls: {learning.stats.tool_calls}, "
        f"runs observed: {learning.stats.runs_observed}"
    )


if __name__ == "__main__":
    asyncio.run(main())
