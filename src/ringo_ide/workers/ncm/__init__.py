"""NCM adapter scaffold; importing it does not import PyTorch or load weights."""

from .backend import NcmBackend

__all__ = ["NcmBackend"]
