"""Configuration records only; no config loader, device probing, or validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class BackendConfig:
    backend: Literal["baseline", "ncm"]
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    model_path: Path | None = None
    tokenizer_path: Path | None = None


@dataclass(frozen=True, slots=True)
class DevicePolicy:
    """Requested precision; supported combinations require future validation."""

    compute_dtype: Literal["float32", "float16", "bfloat16"] = "float32"
    postprocess_dtype: Literal["float32", "float64"] = "float32"
