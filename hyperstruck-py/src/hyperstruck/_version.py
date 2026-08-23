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
# 0.5.3 hardens the rendezvous key a turn's three hook processes share when the host
# supplies no session id of its own. No host the installer wires is in that state today,
# so this moves no production number; the version moves because the User-Agent is the only
# way a fleet is segmented, and a wheel that reports the version below it cannot be told
# apart from one without the change.
# 0.5.4 is the first release that names a read-only recall's close as its own decline
# reason rather than borrowing the recording path's. Nothing gates on this value, but the
# User-Agent is the only way a fleet is segmented, so a wheel that reports the version
# below it cannot be told apart from one that still sends the borrowed reason, which is
# exactly what the alert's shrinking loss line has to be read against.
# 0.5.5 changes four things a fleet must be able to tell apart, and they land together
# because one wheel is one shipped artefact and one version names it.
#   * A failed tool call is recognised as one. The main host reports a failure by returning
#     its result as a plain string rather than an object, so every structured check missed
#     it and real failures were recorded as successes; a command that merely wrote to stderr
#     was meanwhile recorded as a failure. Both directions at once meant the failure-recovery
#     signal, the one turn class always observed, fired on noise and missed every genuine
#     recovery. Every turn-outcome and failure-count series is read against this boundary.
#   * A failed step now carries the name it failed under, under the single field the server
#     derives a gate from. Every offered rule before this one carried no gate predicate at
#     all, so the gate-derivation rate is read against this boundary or against nothing.
#   * The prompt hook emits the project's previous resolve, so experience reaches the model
#     before it plans rather than after its first tool call. It is deliberately uncreditable
#     and reports itself as such, so a fleet below this version is the control group for
#     whether earlier placement moves the yield at all.
#   * A resolve from the IDE path sends a tool palette and a context window from a
#     registration store that also replaces the tool-name matching which decided what could
#     ever be learned from. The palette-populated ratio and the material-step rate for
#     server-contributed tools are only interpretable per version.
__version__ = "0.5.5"
