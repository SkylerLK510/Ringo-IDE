# Architecture and ownership

Use the [README status table](../README.md#what-works-today) to distinguish
implementation from plans, and the [roadmap](ROADMAP.md) for work packages.

## Separate responsibilities

- **Editor host:** live documents, identities, context, admission, deadlines,
  ghost text and undoable edits. UI stack remains undecided.
- **Completion worker:** capabilities, model lifecycle and bounded generation.
  Baseline/NCM implement the same `CompletionBackend` contract.
- **Development harness:** Ringo reviews code/designs outside the editor runtime.

Monitoring is an independent policy hook. It can later use deterministic editor
or language-server signals. No remote escalation client is implemented.

## Request lifecycle

The [demo](../src/ringo_ide/demo.py) executes snapshot → request → fixture result
→ validation → in-memory replacement. Asynchronous/editor behavior below is
planned:

1. Capture a complete authoritative snapshot; hash UTF-8 bytes with SHA-256.
   Track document incarnation/version. Reopening creates a new incarnation;
   restarting a worker creates a new session.
2. Convert editor coordinates against that snapshot. Select a host-owned
   half-open UTF-8 range and bounded prefix/suffix context. Context lengths do
   not determine authoritative edit offsets.
3. Build `CompletionRequest` with session/request/document identity, language,
   trained output bucket and remaining duration budget.
4. Admit against negotiated capabilities. Keep one active and one replaceable
   pending generation per device across documents/backends. Record a monotonic
   deadline; superseding editor events cancel obsolete work.
5. Receive complete replacement text or a terminal outcome. Only `complete`
   carries an editable payload; empty generation becomes `no_suggestion`.
   The worker never chooses a different edit range.
6. Before display check live session/request, document version/hash,
   cancellation and deadline; then validate snapshot/range/payload.
7. Repeat live checks before acceptance. Apply the original range through one
   atomic undoable transaction. Never silently rebase stale results.

`SnapshotEditValidator` checks matching identities, complete-text hash, ordered
in-bounds UTF-8/CRLF ranges, valid UTF-8, nonempty output and replacement byte cap.
`apply_completion` returns a new string. It does not write files, implement undo,
check syntax/types, or verify live request/deadline/cancellation state. A valid
snapshot is necessary but not sufficient for displaying a live suggestion.

## Protocol and scheduling boundary

[messages.py](../src/ringo_ide/protocol/messages.py) uses immutable dataclasses;
annotations do not validate runtime input. The demo's `asdict` JSON is diagnostic
output, not an implemented production wire schema.

The proposed transport is bounded UTF-8 JSONL on stdin/stdout, with logs on
stderr. Implement a codec that validates types, versions, discriminators, IDs,
digests, frame sizes and limits before generation. Define unknown/duplicate
field handling. Negotiate tasks, trained buckets, token/frame/output limits,
device/dtype and immutable model/tokenizer/config revisions at startup.
Actual token counts require the selected tokenizer, not a byte-count estimate.
Fixture capability values are test metadata, not measured model support.

Every admitted request needs one terminal host outcome while its session is
alive: `complete`, `no_suggestion`, `cancelled`, `expired`, or `error`. Discard
late/duplicate responses. Process loss terminalizes outstanding work and
invalidates its session. Unknown/already-terminal cancel IDs are harmless.

`SuggestionScheduler` remains a Protocol. Build it with controlled fixtures and
an injectable clock. Replacing pending work terminalizes it. Cancelling active
work does not free its slot until execution returns or the process exits.
Input reading must remain independent of inference; one executor owns mutable
model/cache state. A cancellation flag cannot interrupt an already dispatched
GPU kernel. Watchdog restarts must be bounded/asynchronous with fresh sessions;
a fallback cannot exceed the original deadline.

## NCM and source preservation

Adapt prompt encoding, hierarchy generation, reconstruction and final text
selection behind the existing backend contract. No latent tensor belongs in the
editor. Keep source bytes, paths, symbols and diagnostics independently of
learned representations. See [NCM integration](NCM_INTEGRATION.md).

Do not add model loading/network requests to top-level imports. Future model
libraries belong behind optional installation and explicit worker startup.
Config records are not certification of CPU/CUDA/MPS support. Training and
benchmarking remain separate from editing.
