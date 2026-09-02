"""Agent identity for the Hyperstruck learning client.

A client-side value type, deliberately independent of any Core import: the public
package never depends on ``hyperstruck_core``. ``agent_name`` is the customer's
human-readable agent name (e.g. ``"support-bot"``). If that name does not exist in
your tenant yet, the learning boundary **creates an agent with that name** on
first use and scopes the corpus to it. This is **not** the hosted agent UUID used
in ``/agents/{agent_id}`` REST paths — set ``HYPER_AGENT_ID`` for those calls
instead.

``org_id`` is optional and resolved server-side from the API key, so a single
tenant need only set ``agent_name``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    """Which corpus a boundary run reads from and writes to.

    Frozen and hashable so it can key a per-invoke resolver cache and be compared
    for the registration-vs-override check in the middleware.
    """

    agent_name: str
    org_id: str | None = None

    def __post_init__(self) -> None:
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("AgentIdentity requires a non-empty agent_name")
