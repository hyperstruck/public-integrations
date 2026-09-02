"""IDE host for Hyperstruck learning: Claude Code and Cursor.

The editor-driven analogue of the LangGraph middleware. Editor hooks run the
resolve / observe / reinforce loop across separate processes, sharing per-turn
state on disk, so learning happens automatically while you code with no explicit
skill calls in the common case. Install it with::

    python -m hyperstruck.ide.install

The framework-neutral client, identity, and wire types it builds on live at the
package top level. The install and hook entry points are run as modules
(``python -m hyperstruck.ide.install`` / ``hyperstruck.ide.hook``); import them by
their submodule (e.g. ``from hyperstruck.ide.install import install``) when calling
programmatically, so the ``install`` submodule is never shadowed by a re-export.
"""

from __future__ import annotations
