"""The hook loop's one diagnostic channel.

Lives apart from :mod:`hyperstruck.ide.hook` so the modules the hook calls can use it
too. A hook runs as a short-lived editor-spawned process with no logging configuration,
so a ``logging`` call there reaches nobody: the diagnostic exists to be read while
debugging a silent loop, and one that goes nowhere is worse than none, because it reads
as coverage.
"""

from __future__ import annotations

import os
import sys

from hyperstruck.ide.constants import HOOK_DEBUG_ENV, HOOK_DEBUG_OFF_VALUES


def debug(message: str) -> None:
    """Write one diagnostic breadcrumb to stderr when ``HYPER_HOOK_DEBUG`` is set.

    stderr, never stdout: stdout carries the injection JSON and must stay clean.
    Guarded so it can never raise and break the loop's fail-open contract.
    """
    if (os.environ.get(HOOK_DEBUG_ENV) or "").strip().lower() in HOOK_DEBUG_OFF_VALUES:
        return
    try:
        sys.stderr.write(f"[hyperstruck-hook] {message}\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass
