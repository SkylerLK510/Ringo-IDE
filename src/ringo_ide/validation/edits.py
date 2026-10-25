"""Validation interface; no range checks, hashing, parsing, or mutation yet."""

from typing import Protocol

from ringo_ide.editor.context.provider import DocumentSnapshot
from ringo_ide.protocol.messages import CompletionRequest, WorkerResult


class EditValidator(Protocol):
    def validate(
        self,
        snapshot: DocumentSnapshot,
        request: CompletionRequest,
        result: WorkerResult,
    ) -> None:
        """Reject stale identities and invalid ranges/payloads; not implemented."""
        ...
