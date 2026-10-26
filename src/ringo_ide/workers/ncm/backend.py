"""NCM adapter stub; generation, reconstruction, and decoding remain unimplemented."""

from dataclasses import dataclass, field

from ringo_ide.protocol.messages import (
    CompletionRequest,
    WorkerCapabilities,
    WorkerResult,
)
from ringo_ide.workers.base import CancellationSignal
from ringo_ide.workers.config import BackendConfig, DevicePolicy


@dataclass(frozen=True, slots=True)
class NcmBackend:
    config: BackendConfig
    device_policy: DevicePolicy = field(default_factory=DevicePolicy)

    def capabilities(self) -> WorkerCapabilities:
        raise NotImplementedError("NCM capabilities are scaffolding only.")

    def complete(
        self, request: CompletionRequest, cancellation: CancellationSignal
    ) -> WorkerResult:
        raise NotImplementedError("NCM model inference is not implemented.")

    def close(self) -> None:
        raise NotImplementedError("NCM worker lifecycle is not implemented.")
