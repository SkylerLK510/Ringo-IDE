"""Context selection interface; no parser, retrieval, or coordinate conversion."""

from dataclasses import dataclass
from typing import Protocol

from ringo_ide.protocol.messages import ByteRange, DocumentVersion


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    document: DocumentVersion
    text: str


@dataclass(frozen=True, slots=True)
class CompletionContext:
    prefix: str
    suffix: str
    language: str


class ContextProvider(Protocol):
    def select(
        self,
        snapshot: DocumentSnapshot,
        edit_range: ByteRange,
        token_budget: int,
    ) -> CompletionContext:
        """Select context from the authoritative snapshot; not implemented."""
        ...
