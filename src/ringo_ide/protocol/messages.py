"""Typed scaffolding for the proposed local-worker protocol.

These records do not validate input or define a JSONL representation. A future
boundary must validate versions, identities, limits, hashes, and byte ranges.
"""

from dataclasses import dataclass, field
from typing import Literal

PROTOCOL_VERSION = 1
TaskKind = Literal["complete_span"]
TerminalStatus = Literal["no_suggestion", "cancelled", "expired", "error"]


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    """A document incarnation and the SHA-256 of its complete UTF-8 snapshot."""

    document_id: str
    version: int
    sha256: str


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    session_id: str
    request_id: str
    document: DocumentVersion


@dataclass(frozen=True, slots=True)
class ByteRange:
    """Host-owned half-open UTF-8 range; bounds/boundaries are not checked here."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    identity: RequestIdentity
    edit_range_utf8: ByteRange
    prefix: str
    suffix: str
    language: str
    output_bucket_tokens: int
    budget_ms: int
    task: TaskKind = field(default="complete_span", init=False)
    protocol_version: int = field(default=PROTOCOL_VERSION, init=False)


@dataclass(frozen=True, slots=True)
class CancelRequest:
    session_id: str
    request_id: str
    protocol_version: int = field(default=PROTOCOL_VERSION, init=False)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    identity: RequestIdentity
    replacement_text: str
    status: Literal["complete"] = field(default="complete", init=False)
    protocol_version: int = field(default=PROTOCOL_VERSION, init=False)


@dataclass(frozen=True, slots=True)
class TerminalResult:
    """A terminal outcome without an editable payload."""

    identity: RequestIdentity
    status: TerminalStatus
    reason_code: str
    protocol_version: int = field(default=PROTOCOL_VERSION, init=False)


WorkerResult = CompletionResult | TerminalResult


@dataclass(frozen=True, slots=True)
class WorkerCapabilities:
    """Future handshake data; declarations do not establish backend support."""

    backend_name: str
    tasks: tuple[TaskKind, ...]
    output_buckets: tuple[int, ...]
    max_context_tokens: int
    max_frame_bytes: int
    max_output_bytes: int
    device: str
    dtype: str
    model_revision: str | None
    tokenizer_revision: str | None
    config_revision: str | None
    protocol_version: int = field(default=PROTOCOL_VERSION, init=False)
