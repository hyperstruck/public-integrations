"""The hook loop's binding of the package diagnostic channel.

Lives apart from :mod:`hyperstruck.ide.hook` so the modules the hook calls can use it too,
and tags every line as the hook's so a reader greping for a silent loop sees the hook's
breadcrumbs and not the neutral layer's.
"""

from __future__ import annotations

from hyperstruck.debug import debug as _debug

HOOK_CHANNEL = "hyperstruck-hook"


def debug(message: str) -> None:
    """Write one hook-tagged diagnostic breadcrumb, per :func:`hyperstruck.debug.debug`."""
    _debug(message, channel=HOOK_CHANNEL)
