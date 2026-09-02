"""One env-gated diagnostic channel, shared by every layer of the package.

A hook runs as a short-lived editor-spawned process with no logging configuration, so a
``logging`` call there reaches nobody: the diagnostic exists to be read while debugging a
silent loop, and one that goes nowhere is worse than none, because it reads as coverage.

It lives at the top level rather than under :mod:`hyperstruck.ide` because the vendored
contract reader is framework-neutral and degrades silently when a contract is unreadable,
which is exactly the state worth a breadcrumb. Importing the hook's channel to get one made
the neutral layer depend on the IDE adapter, and labelled a LangGraph host's diagnostic as
the hook's.

``channel`` is what the line is tagged with, so a reader greping for the hook still finds
only the hook. The switch is deliberately one variable for all channels: two would mean a
user who set the one they had heard of would see silence and read it as no events.
"""

from __future__ import annotations

import os
import sys

from hyperstruck.env import DEBUG_ENV, DEBUG_OFF_VALUES

DEFAULT_CHANNEL = "hyperstruck"


def debug(message: str, *, channel: str = DEFAULT_CHANNEL) -> None:
    """Write one diagnostic breadcrumb to stderr when ``HYPER_HOOK_DEBUG`` is set.

    stderr, never stdout: stdout carries the injection JSON and must stay clean.
    Guarded so it can never raise and break the loop's fail-open contract.
    """
    if (os.environ.get(DEBUG_ENV) or "").strip().lower() in DEBUG_OFF_VALUES:
        return
    try:
        sys.stderr.write(f"[{channel}] {message}\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass
