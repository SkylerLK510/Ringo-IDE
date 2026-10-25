"""Baseline adapter stub; no llama.cpp process, model, or HTTP client."""

from dataclasses import dataclass

from ringo_ide.protocol.messages import (
    CompletionRequest,
    WorkerCapabilities,
    WorkerResult,
)
from ringo_ide.workers.base import CancellationSignal
from ringo_ide.workers.config import BackendConfig


@dataclass(frozen=True, slots=True)
class BaselineBackend:
    config: BackendConfig

    def capabilities(self) -> WorkerCapabilities:
        raise NotImplementedError("Baseline capabilities are scaffolding only.")

    def complete(
        self, request: CompletionRequest, cancellation: CancellationSignal
    ) -> WorkerResult:
        raise NotImplementedError("Baseline model inference is not implemented.")

    def close(self) -> None:
        raise NotImplementedError("Baseline worker lifecycle is not implemented.")
