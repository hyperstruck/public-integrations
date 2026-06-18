"""Agent identity for the Hyperstruck learning client.

A client-side value type, deliberately independent of any Core import: the public
package never depends on ``hyperstruck_core``. ``agent_id`` is the customer's own
string (e.g. ``"support-bot"``); the platform auto-upserts a named agent on first
use and scopes the corpus to it. ``org_id`` is optional and resolved server-side
from the API key, so a single tenant need only set ``agent_id``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    """Which corpus a run reads from and writes to.

    Frozen and hashable so it can key a per-invoke resolver cache and be compared
    for the registration-vs-override check in the middleware.
    """

    agent_id: str
    org_id: str | None = None

    def __post_init__(self) -> None:
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("AgentIdentity requires a non-empty agent_id")
