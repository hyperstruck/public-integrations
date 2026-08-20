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
# 0.5.1 is the first release that parses the recalled-fact block a resolve now returns
# separately from the advice block. Additive only: it changes nothing about the receipt the
# 0.5.0 gate reads, and an older client against the new server simply never sees the facts.
# 0.5.2 is the first release that reports whether the recall it was handed ever reached
# the model. A turn that was never shown its recall owes no receipt, so without this the
# server can only read the missing receipt as a client defect. Moving the version is what
# lets a fleet still running 0.5.1 be told apart from one that can answer the question.
__version__ = "0.5.2"
