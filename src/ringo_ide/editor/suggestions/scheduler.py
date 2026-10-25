"""Future host scheduler boundary.

The implementation must coordinate one active and one replaceable pending
request per device, deadlines, terminal outcomes, and stale-result rejection.
This Protocol supplies no state machine or concurrency guarantees.
"""

from typing import Protocol

from ringo_ide.protocol.messages import (
    CancelRequest,
    CompletionRequest,
    WorkerResult,
)


class SuggestionScheduler(Protocol):
    def submit(self, request: CompletionRequest) -> None:
        """Queue work without blocking the editor; not implemented."""
        ...

    def cancel(self, request: CancelRequest) -> None:
        """Mark obsolete work for cancellation; not implemented."""
        ...

    def receive(self, result: WorkerResult) -> None:
        """Check identity/deadline before display or application; not implemented."""
        ...
