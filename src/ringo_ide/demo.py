"""Offline vertical slice: snapshot -> fixture -> validation -> in-memory edit."""

from dataclasses import asdict
from hashlib import sha256
from threading import Event

from ringo_ide.editor.context.provider import DocumentSnapshot
from ringo_ide.protocol.messages import (
    ByteRange,
    CompletionRequest,
    DocumentVersion,
    RequestIdentity,
)
from ringo_ide.validation.edits import apply_completion
from ringo_ide.workers.fixture import FixtureBackend


class EventCancellation:
    def __init__(self, event: Event) -> None:
        self.event = event

    def is_cancelled(self) -> bool:
        return self.event.is_set()


def run_demo() -> dict[str, object]:
    """Return a reproducible example; no files, processes or models are opened."""
    prefix = "def greet(name):\n    "
    suffix = "\n"
    before = prefix + suffix
    document = DocumentVersion("demo-document", 1, sha256(before.encode()).hexdigest())
    snapshot = DocumentSnapshot(document, before)
    cursor = len(prefix.encode("utf-8"))
    request = CompletionRequest(
        identity=RequestIdentity("demo-session", "demo-request", document),
        edit_range_utf8=ByteRange(cursor, cursor), prefix=prefix, suffix=suffix,
        language="python", output_bucket_tokens=64, budget_ms=200,
    )
    backend = FixtureBackend(request, 'return f"Hello, {name}!"')
    try:
        result = backend.complete(request, EventCancellation(Event()))
        after = apply_completion(
            snapshot, request, result,
            max_output_bytes=backend.capabilities().max_output_bytes,
        )
        return {"backend": "fixture", "model_inference": False,
                "before": before, "request": asdict(request),
                "result": asdict(result), "after": after}
    finally:
        backend.close()
