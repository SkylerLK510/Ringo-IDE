"""Single-request fixture implementation of CompletionBackend.

This backend performs no inference and makes no quality/latency claims. It is
synchronous; cancellation is checked at entry, not during simulated device work.
"""

from ringo_ide.protocol.messages import (
    CompletionRequest,
    CompletionResult,
    TerminalResult,
    WorkerCapabilities,
    WorkerResult,
)
from ringo_ide.workers.base import CancellationSignal


class FixtureBackend:
    def __init__(self, expected: CompletionRequest, replacement_text: str) -> None:
        self.expected = expected
        self.replacement_text = replacement_text
        self.closed = False

    def capabilities(self) -> WorkerCapabilities:
        if self.closed:
            raise RuntimeError("Fixture backend is closed")
        return WorkerCapabilities(
            backend_name="fixture", tasks=("complete_span",),
            output_buckets=(64,), max_context_tokens=512,
            max_frame_bytes=65536, max_output_bytes=4096,
            device="cpu", dtype="fixture-text",
            model_revision=None, tokenizer_revision=None,
            config_revision="fixture-v1",
        )

    def complete(
        self, request: CompletionRequest, cancellation: CancellationSignal
    ) -> WorkerResult:
        if self.closed:
            raise RuntimeError("Fixture backend is closed")
        if cancellation.is_cancelled():
            return TerminalResult(request.identity, "cancelled", "host_cancelled")
        if request != self.expected:
            return TerminalResult(request.identity, "error", "fixture_mismatch")
        if request.output_bucket_tokens != 64 or request.budget_ms <= 0:
            return TerminalResult(request.identity, "error", "unsupported_request")
        if len(self.replacement_text.encode("utf-8")) > 4096:
            return TerminalResult(request.identity, "error", "output_too_large")
        if not self.replacement_text:
            return TerminalResult(request.identity, "no_suggestion", "empty_fixture")
        return CompletionResult(request.identity, self.replacement_text)

    def close(self) -> None:
        self.closed = True
