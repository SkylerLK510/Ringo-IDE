"""Snapshot/range validation and an in-memory reference edit application.

These checks are for trusted in-process records. They are not a wire decoder,
syntax/type checker, deadline check, or an editor transaction implementation.
"""

from hashlib import sha256
from typing import Protocol

from ringo_ide.editor.context.provider import DocumentSnapshot
from ringo_ide.protocol.messages import (
    PROTOCOL_VERSION,
    CompletionRequest,
    CompletionResult,
    WorkerResult,
)


class EditValidator(Protocol):
    def validate(
        self,
        snapshot: DocumentSnapshot,
        request: CompletionRequest,
        result: WorkerResult,
    ) -> None:
        """Reject stale identities and invalid ranges/payloads; not implemented."""
        ...


class InvalidEdit(ValueError):
    """A candidate cannot be applied to the supplied authoritative snapshot."""


class SnapshotEditValidator:
    """Validate identity, UTF-8/CRLF boundaries and replacement byte size."""

    def __init__(self, max_output_bytes: int = 65536) -> None:
        if type(max_output_bytes) is not int or max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be a positive integer")
        self.max_output_bytes = max_output_bytes

    def validate(
        self,
        snapshot: DocumentSnapshot,
        request: CompletionRequest,
        result: WorkerResult,
    ) -> None:
        if not isinstance(result, CompletionResult):
            raise InvalidEdit("Only a complete result carries an editable payload")
        if (request.protocol_version != PROTOCOL_VERSION
                or result.protocol_version != PROTOCOL_VERSION):
            raise InvalidEdit("Unsupported protocol version")
        if (request.identity != result.identity
                or request.identity.document != snapshot.document):
            raise InvalidEdit("Stale or mismatched request/document identity")
        try:
            source = snapshot.text.encode("utf-8")
            replacement = result.replacement_text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidEdit("Source and replacement must be valid UTF-8") from exc
        if sha256(source).hexdigest() != snapshot.document.sha256:
            raise InvalidEdit("Snapshot hash does not match its complete UTF-8 text")
        start, end = request.edit_range_utf8.start, request.edit_range_utf8.end
        if type(start) is not int or type(end) is not int:
            raise InvalidEdit("Byte offsets must be integers")
        if not 0 <= start <= end <= len(source):
            raise InvalidEdit("Edit range is outside the snapshot")
        for offset in (start, end):
            if offset < len(source) and source[offset] & 0xC0 == 0x80:
                raise InvalidEdit("Edit range splits a UTF-8 code point")
            if 0 < offset < len(source) and source[offset - 1:offset + 1] == b"\r\n":
                raise InvalidEdit("Edit range splits a CRLF newline")
        if not replacement:
            raise InvalidEdit("Empty generation must be a no_suggestion result")
        if len(replacement) > self.max_output_bytes:
            raise InvalidEdit("Replacement exceeds max_output_bytes")


def apply_completion(
    snapshot: DocumentSnapshot,
    request: CompletionRequest,
    result: WorkerResult,
    *,
    max_output_bytes: int = 65536,
) -> str:
    """Return edited text without mutating a document or writing any files.

    A real host must also check its live session, active request, deadline and
    cancellation state, then apply through an atomic undoable editor transaction.
    """
    SnapshotEditValidator(max_output_bytes).validate(snapshot, request, result)
    assert isinstance(result, CompletionResult)
    source = snapshot.text.encode("utf-8")
    edit = request.edit_range_utf8
    return (source[:edit.start] + result.replacement_text.encode("utf-8")
            + source[edit.end:]).decode("utf-8")
