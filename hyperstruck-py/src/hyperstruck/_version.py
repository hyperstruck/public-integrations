"""The package version, in a leaf module so anything may import it.

``__init__`` imports the client, so the client cannot import the version back from
``__init__`` without a cycle. It lives here instead, and ``__init__`` re-exports it
as the public ``__version__``.
"""

from __future__ import annotations

# 0.5.0 is the first release that posts an exposure receipt, and the server's adoption
# gate reads exactly that boundary out of the User-Agent. Shipping the receipt code
# without moving this would leave every capable and incapable client reporting the same
# string, which is what made the gate read 100% safe on a fleet that could send nothing.
__version__ = "0.5.0"
