"""The framework-neutral run seat: one core, attachable from any runtime."""

from __future__ import annotations

from hyperstruck.runtime.agent_framework import HyperstruckContextProvider
from hyperstruck.runtime.declarations import DeclarationRegistry, ToolDeclaration
from hyperstruck.runtime.handle import hyperstruck_run
from hyperstruck.runtime.ledger import (
    LedgerClosedError,
    LedgerStateError,
    RunLedger,
    Shelf,
)
from hyperstruck.runtime.model_seat import (
    WrappedModelClient,
    wrap_anthropic,
    wrap_openai,
)
from hyperstruck.runtime.otel import (
    conversation_run_key,
    resolvers_with_conversation,
)
from hyperstruck.runtime.receipt import ReceiptLocation, ShelfFidelity, locate_receipt
from hyperstruck.runtime.resilience import CircuitOpenError
from hyperstruck.runtime.run import (
    CLOSE_TRIGGER_ABANDONED,
    DISPOSITION_DECLINED,
    DISPOSITION_EVICTED,
    DISPOSITION_OBSERVED,
    DISPOSITION_REINFORCED,
    DISPOSITION_WITHHELD,
    DISPOSITION_WRITE_FAILED,
    CLOSE_TRIGGER_EXPLICIT,
    CLOSE_TRIGGER_NO_TOOL_CALLS,
    CLOSE_TRIGGER_PROCESS_EXIT,
    HyperstruckRun,
    RunRegistry,
    RunReport,
    RunSeat,
)
from hyperstruck.runtime.run_key import RunKey, resolve_run_key
from hyperstruck.runtime.scanning import (
    CompositeScanner,
    ContentScanner,
    Finding,
    NullScanner,
    PresidioScanner,
)

__all__ = [
    "CLOSE_TRIGGER_ABANDONED",
    "CLOSE_TRIGGER_EXPLICIT",
    "CLOSE_TRIGGER_NO_TOOL_CALLS",
    "CLOSE_TRIGGER_PROCESS_EXIT",
    "CircuitOpenError",
    "CompositeScanner",
    "ContentScanner",
    "DISPOSITION_DECLINED",
    "DISPOSITION_EVICTED",
    "DISPOSITION_OBSERVED",
    "DISPOSITION_REINFORCED",
    "DISPOSITION_WITHHELD",
    "DISPOSITION_WRITE_FAILED",
    "DeclarationRegistry",
    "Finding",
    "HyperstruckContextProvider",
    "HyperstruckRun",
    "LedgerClosedError",
    "LedgerStateError",
    "NullScanner",
    "PresidioScanner",
    "ReceiptLocation",
    "RunKey",
    "RunLedger",
    "RunRegistry",
    "RunReport",
    "RunSeat",
    "Shelf",
    "ShelfFidelity",
    "ToolDeclaration",
    "WrappedModelClient",
    "conversation_run_key",
    "hyperstruck_run",
    "locate_receipt",
    "resolve_run_key",
    "resolvers_with_conversation",
    "wrap_anthropic",
    "wrap_openai",
]
