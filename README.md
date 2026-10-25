# Ringo-IDE

Experimental IDE research exploring a local monitor and next-concept modeling
(NCM) for code suggestions.

This checkout is **scaffolding only**. It defines Python contracts and backend
stubs; it does not implement an editor, worker transport, request scheduling,
model loading, inference, training, or benchmarking. Importing the package does
not load models or start processes. No model dependencies are installed.

## Layout

```text
src/ringo_ide/
  protocol/             Typed request, result, cancellation, and capability records
  editor/context/       Document snapshots and context-selection interface
  editor/suggestions/   Scheduler interface
  monitoring/           Monitoring-policy interface, separate from generation
  workers/              Shared backend contract and configuration
    baseline/           Small-code-model adapter stub
    ncm/                NCM adapter stub
  validation/           Edit-validation interface
configs/                Illustrative worker configuration
research/ncm_training/  Future representation and generator training boundary
benchmarks/completion/  Future completion replay and measurement boundary
```

The Python package is the worker-side reference scaffold; it does not select an
editor UI language or framework. The dataclasses are in-process contracts, not
a JSONL codec or validated wire schema. Backend operations explicitly raise
`NotImplementedError`. Scheduler, cancellation, snapshot, range, and capability
rules still need implementation before this can serve requests.

## Local checks

Python 3.11 or newer is sufficient for syntax and import checks:

```sh
python3 -m compileall -q src
PYTHONPATH=src python3 -c 'import ringo_ide.workers.baseline; import ringo_ide.workers.ncm'
```

There is no runnable worker command yet. The example configuration is not loaded
by the package. Model selection, device support, and performance remain open.

## Research

- [NCM architecture research](docs/NCM_ARCHITECTURE_RESEARCH.md)
- [Implementation methods and proposed gates](docs/NCM_IMPLEMENTATION_METHODS.md)
