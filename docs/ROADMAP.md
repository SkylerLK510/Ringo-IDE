# Roadmap and collaborator tasks

These are bounded work packages, not promised dates or approved training runs.
Choose an owner per PR. Skyler and the collaborator can split host infrastructure
and ML work after agreeing on the open product decisions below.

## S0 — handoff scaffold (available)

Package/CLI, fixed fixture backend, typed interfaces, snapshot/range validator,
in-memory edit application, tests/CI, onboarding and NCM integration map.

**Gate:** a fresh clone can run the README demo and tests without model assets.
This does not mean the asynchronous worker or IDE exists.

## S1 — host/worker contract (first engineering milestone)

| Task | Starting files | Completion criteria |
|---|---|---|
| JSONL codec/handshake | `protocol/messages.py`; new codec/tests | Bounded frames; field/type/version/ID validation; malformed/oversized input and unsupported capabilities rejected; stdout protocol-only |
| Scheduler | `editor/suggestions/scheduler.py`; controlled fixtures | One active/one replaceable pending per device; injected clock; terminalize once; supersession, cancellation, expiry, late/duplicate response tests |
| Worker runner | New worker entrypoint/transport | Independent input reader; one inference executor; bounded shutdown/restart; fresh session after crash |
| Snapshot/context bridge | `editor/context/provider.py`, `validation/edits.py` | Snapshot-specific editor/UTF-8 mapping; Unicode/CRLF tests; token budgeting; live display/accept checks; atomic undo |
| Config loader | `workers/config.py`, `configs/worker.example.toml` | Validated records; clear unsupported-setting errors; parsing/import does not load models |

Codec and scheduler can proceed against fixtures; the runner depends on both.
Editor transactions require a host choice. Keep state-machine/transport tests
independent of UI. **Suggested first collaborator PR:** codec with malformed
frames; next, scheduler with delayed, failed and reordered fixture responses.
No GPU is needed. The synchronous demo does not test concurrency.

## S2 — real baseline and replay

Implement `workers/baseline/backend.py` with a pinned small code model/runtime
and its actual fill-in-the-middle format. The prior research proposes a
Qwen2.5-Coder-1.5B comparator; selection remains open. Model libraries should be
optional and loading explicit. Add a replay runner in `benchmarks/completion/`.

**Gate:** valid requests complete through S1; crash/cancel/stale work cannot edit
changed documents. Record cold startup, batch-one complete-suggestion latency,
resources and all outcomes. The fixed fixture is not a model baseline.

## S3 — NCM reference compatibility

Implement artifact manifests and the stage-isolated adapter in `workers/ncm/`
using [NCM_INTEGRATION](NCM_INTEGRATION.md). Reconstruction probes can start
independently of S2; adoption comparisons need a real baseline.

**Gate:** artifacts load strictly; stage fixtures match the intended reference;
account for device/dtype differences and cancellation points. Reproducing a
released task establishes compatibility, not code-completion capability.

## S4 — fidelity and conditional code training

Build raw/learned tokenizer probes in `research/ncm_training/`. After fidelity
passes, implement frozen-representation prefix/suffix training, reproducible data
splits, checkpoint/resume and validation decoding.

**Gate:** raw fixtures round-trip exactly; declared learned-representation
validation has no observed critical-symbol changes, with counts/categories
reported. Zero observed failures does not prove universal losslessness. A
trained generator must meet a predeclared held-out quality floor. Agree on data,
hardware and finite budgets before running training.

## S5 — editor integration and measured optimization

Connect the selected UI to S1/S2 with ghost text, explicit acceptance/undo and a
separate deterministic monitor. Connect NCM as S3/S4 pass. Profile before adding
compilation, quantization, platform ports or length/task routing.

**Gate:** paired held-out replay meets quality, responsiveness and memory bounds,
including cancelled/no-suggestion/error outcomes and uncertainty. Adopt NCM only
on useful measured benefit; otherwise retain the common baseline.

## Decisions to agree before model/training work

| Decision | Current state |
|---|---|
| Editor UI/host language and packaging | Open; Python reference worker only |
| Initial hardware/OS/runtime | Open; config literals are not device support |
| Code language/source encoding | Python demo; production scope open; UTF-8 reference offsets |
| Baseline and artifact revisions | Open; no weights bundled |
| Latency/cancellation/memory thresholds | Open; demo budget is illustrative |
| Licensed data and repository/time split | Open; no dataset bundled |
| Training/teacher/compute budgets | Open; no run launched |

S1 infrastructure work does not depend on choosing model/training settings.
Record decisions and evidence in the relevant guide and PR.
