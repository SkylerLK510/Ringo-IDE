"""Shared contract for future baseline and NCM adapters."""

from typing import Protocol

from ringo_ide.protocol.messages import (
    CompletionRequest,
    WorkerCapabilities,
    WorkerResult,
)


class CancellationSignal(Protocol):
    def is_cancelled(self) -> bool:
        """Read cancellation state; this contract does not stop device work."""
        ...


class CompletionBackend(Protocol):
    def capabilities(self) -> WorkerCapabilities:
        """Describe a loaded, validated backend; not implemented."""
        ...

    def complete(
        self, request: CompletionRequest, cancellation: CancellationSignal
    ) -> WorkerResult:
        """Generate one result under host scheduling; not implemented."""
        ...

    def close(self) -> None:
        """Release backend resources; not implemented."""
        ...
