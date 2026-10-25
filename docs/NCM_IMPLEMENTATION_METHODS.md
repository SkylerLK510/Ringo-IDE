# Effective implementation methods for NCM in Ringo-IDE

Research date: October 24, 2026. This extends [the architecture research](NCM_ARCHITECTURE_RESEARCH.md). It proposes implementation work; no NCM weights were executed, no model was trained, and no IDE performance was measured. Hardware, supported languages, product latency targets, and training budgets remain unspecified. Recommendations below are engineering judgments informed by primary sources, not demonstrated performance rankings.

## Recommended approach

**Build a model-independent local worker interface and a working code-completion baseline, then train and evaluate a code-specific NCM behind the same interface. Keep monitoring separate from generation.** This sequence makes the UI, context selection, cancellation, validation, and measurement reusable even if the NCM experiment does not succeed.

The best first use of NCM is a bounded, complete code suggestion. A monitor that mainly labels an event, ranks context, or requests escalation should first use deterministic editor/language-server signals; consider a compact classifier only if labeled examples show a gap. NCM's generation hierarchy does not establish an advantage for a one-label output.

| Method | Recommended use | Main limitation |
|---|---|---|
| Existing small code model behind a local worker | First usable completion system and comparison baseline | Does not test NCM's architectural benefit |
| Unmodified released NCM weights | Loading, decoding, and reconstruction investigation | Released tasks do not establish code completion [R1] |
| Adapt the NCM generator while reusing its learned tokenizer | Conditional shortcut if code reconstruction passes first | Tokenizer errors remain; context/task adaptation still needs training |
| Train a code tokenizer and conditional NCM generator | Preferred research route when reuse fails | Two training stages plus deployment engineering |
| NCM proposals checked by an autoregressive model | Later experiment if a verifier is already available | Two-model memory, verification latency, and probability-interface complications |
| Native MLX/Core ML/C++ NCM rewrite | Later deployment optimization after profiling | Porting correctness before evidence of a bottleneck adds work |

Rank the implementation methods as follows: (1) rules/LSP monitoring plus a separate small-code-model completion baseline; (2) a persistent eager Python NCM worker for research; (3) selectively optimized PyTorch on the selected device; (4) custom MLX or per-stage Core ML; (5) a native inference rewrite. Within the NCM experiment, probe released weights, reuse the tokenizer only if reconstruction passes, and otherwise train both stages. These are engineering priorities, not measured winners. The goal is to discover whether NCM offers a useful quality/latency/energy tradeoff on the actual device.

## 1. Establish the shared completion system first

The current Ringo-IDE checkout tracks a README describing a future 1.5B monitor and a license; its existing documents are research. No implemented editor/model integration was found. The following is a proposed module layout, not a description of existing code:

```text
editor/context/             syntax scope, prefix/suffix, symbol information
editor/suggestions/         request scheduling, versions, ghost-text display
protocol/                   typed requests, responses, cancellation, capabilities
workers/baseline/            adapter to a pinned small code-model runtime
workers/ncm/                 PyTorch reference and optional device-specific backend
validation/                  edit-range checks and bounded syntax checks
research/ncm_training/       future tokenizer/generator training implementation
benchmarks/completion/       replay traces and offline quality/latency measurement
```

Use the eventual IDE's host language for the editor and scheduler. Use a persistent Python process for the first NCM worker so the research implementation stays close to upstream. Start with bounded JSON messages over standard input/output: no network server is necessary for this worker. Reserve standard output for protocol messages and standard error for logs. Add a maximum message size, startup handshake, deadline, and explicit error responses. This transport is a proposed prototype choice; profile serialization before replacing it with shared memory or FFI.

For the baseline, recommend **Qwen2.5-Coder-1.5B base** as a documented comparator close to the planned model scale. Its publisher identifies 1.54B parameters and supports fill-in-the-middle use while discouraging conversation with the base model. This is not a claim that it is today's best small coder. Use its pinned FIM format rather than a generic chat template. [R2]

`llama.cpp` documents CPU, Metal, CUDA, and quantized inference; its server exposes `/infill` with prefix and suffix inputs. That makes it a practical baseline adapter candidate, subject to checking the exact Qwen model, conversion, prompt tokens, and build. NCM's custom architecture has not been shown to work in that loader. If using the baseline server, bind it locally and manage its lifecycle separately. [R3][R4]

### Context selection and exact edits

Use incremental syntax parsing to select the enclosing scope and relevant imports; add language-server symbol information where available. Tree-sitter documents updating the old tree with an edit and passing it back to the parser for structural reuse. It does not establish a universal submillisecond budget. Start with bounded local context; add repository retrieval only after the local-context baseline is measured. [R5]

Keep the original document authoritative. The host supplies the only permitted insertion/replacement range; the model supplies text for that range. Do not regenerate unchanged file content, file names, or offsets through a latent decoder. Preserve encoding and newline policy explicitly, and test Unicode boundaries. Tree-sitter byte coordinates differ from LSP's negotiated character encoding; LSP defaults to UTF-16 code units. Convert deliberately, not by treating a character count as a byte offset. [R5][R6]

An illustrative, proposed request shape is:

```json
{
  "protocol_version": 1,
  "type": "request",
  "session_id": "example-session",
  "document_id": "example-document",
  "request_id": "completion-42",
  "document_version": 42,
  "document_hash": "sha256:host-computed",
  "task": "complete_span",
  "language": "python",
  "edit_range_utf8": {"start": 120, "end": 120},
  "prefix": "selected context before the cursor",
  "suffix": "selected context after the cursor",
  "output_bucket_tokens": 64,
  "budget_ms": 200
}
```

All protocol identifiers, shapes, model choices, limits, and budget values shown here are illustrative, unvalidated engineering proposals. They do not establish checkpoint support. The request includes required `session_id` and `document_id` fields: request IDs are unique within a worker session, and document versions are meaningful only within a document incarnation. Restarting a worker or reopening a document creates a new identity. The hash must be a real SHA-256 digest of the complete authoritative snapshot's UTF-8 bytes; the displayed hash is a placeholder, not a valid digest. Prefix and suffix are selected context, so neither their lengths nor model token offsets determine the edit range.

Proposed version-1 semantics: a startup handshake negotiates UTF-8 byte offsets, supported tasks and trained buckets, context/frame/output caps, device/dtype, and immutable model/config/tokenizer revisions. Reject unsupported versions and capabilities before generation. Use bounded UTF-8 JSONL frames; reject malformed or oversized frames without loading models or applying edits. An adapter maps the following illustrative response and cancellation shapes onto the same contract:

```json
{
  "protocol_version": 1,
  "type": "result",
  "session_id": "example-session",
  "document_id": "example-document",
  "request_id": "completion-42",
  "document_version": 42,
  "document_hash": "sha256:host-computed",
  "status": "complete",
  "replacement_text": "return value\n"
}
```

```json
{
  "protocol_version": 1,
  "type": "cancel",
  "session_id": "example-session",
  "request_id": "completion-42"
}
```

Require exactly one terminal result for each admitted request while its session remains alive: `complete`, `no_suggestion`, `cancelled`, `expired`, or `error`. Only `complete` carries replacement text; other statuses carry a bounded reason code and no editable payload. Unknown or already terminal cancellation IDs are harmless. Process loss terminalizes its outstanding requests in the host; late or duplicate results are discarded. Workers never choose or modify the host's edit range. Do not manufacture a confidence value from latent-code likelihoods.

Treat the host range as half-open `[start,end)` in the complete snapshot, with `0 <= start <= end <= byte_length`. Reject endpoints inside a UTF-8 code point or between CR and LF. Preserve existing newline bytes and perform no Unicode normalization. The host converts these offsets through a snapshot-specific line index into the editor's negotiated coordinates, testing astral characters, combining marks, tabs, CRLF, empty files, and end-of-file insertion. Before both display and acceptance, require matching session, document incarnation, request ID, revision, full hash, and original host range. Any mismatch discards the candidate without rebasing. Acceptance applies one atomic, undoable replacement against that snapshot.

Compute a host-side monotonic deadline. Send remaining duration rather than an absolute timestamp across processes; adapters subtract elapsed time and the host independently enforces its original deadline. Expired results cannot display, and an empty generation becomes `no_suggestion`.

### Scheduling that remains responsive

Keep at most one active generation and one replaceable pending request per local device. Typing or cursor movement cancels the older request; check request validity again before display and before application. Start with a tunable short idle debounce, then select its value from replay traces instead of promising a particular delay.

The NCM worker should check cancellation and deadlines before initial-code generation, between levels, before final decoding, and before emitting output. The released `generate` API has no cancellation callback, and its output is concatenated code indices. Adding these checks requires an adapted generation loop; a wrapper can only discard completed stale results. A dispatched GPU operation may finish after cancellation. Avoid displaying intermediate reconstructions as stable ghost text. [R7]

If cancellation messages share the worker's stdin, a separate lightweight input reader must update cancellation state while inference runs. A single blocking request loop cannot read the next cancel message until its current inference returns. The reader validates frames and updates bounded scheduler state; a single inference executor owns mutable model/cache state. Do not launch overlapping calls on the same NCM instance. Count the proposed one-active/one-pending limit across documents and backend adapters sharing a device, rather than independently per tab. Replacing pending work terminalizes the replaced request; cancellation does not free the active execution slot until inference actually stops or the process exits.

Neither cancellation acknowledgment nor result disposal proves GPU work has stopped. Keep editor input and protocol reading independent of inference completion. A separately configured watchdog may terminate and asynchronously restart an unresponsive worker; invalidate its session and reload before admitting new work. Cap restart attempts and retain baseline-only operation after repeated failure. On a crash or timeout, terminalize affected requests and clear their state; do not start a fallback that has already exceeded the original deadline.

## 2. Implement the NCM reference adapter before optimizing it

Pin the upstream source to the revision previously inspected, `c70274273f489abc73832b2b98584a8483b6b203`, plus exact checkpoint, text-tokenizer, and config revisions. The earlier report records paper/config differences; resolve those when selecting an artifact rather than substituting a paper's dimensions into a released checkpoint. Retain a reproducible unmodified reference path.

Extract a small inference library from the evaluation script instead of importing its top-level execution. Separate model loading, request encoding, generation, reconstruction, final text decoding, and scoring. The script currently combines argument parsing, checkpoint loading, dataset loading, generation, and metric-oriented output. It explicitly moves the generator and VQ-VAE to CUDA. The generator keeps the VQ-VAE outside its registered module tree, so moving the generator alone is not sufficient. [R8][R7]

Use a device/dtype policy across both components and every temporary tensor. Begin with evaluation mode and gradient-free inference; verify eager outputs before adding compilation. Test a fixed prompt/code fixture through every stage: initial codes, per-level codes/reconstruction, final logits, and text. Treat stochastic sampling equivalence statistically when device random generators differ; use deterministic fixtures to localize numeric disagreements.

### A concrete Apple Silicon blocker

The evaluator's allowance loader calls `.double()`, and its frequency/adjacency token-selection path constructs float64 tensors. PyTorch documents that MPS does not support float64 and that enabling CPU fallback does not permit allocating those tensors on MPS. Thus replacing `.cuda()` with `.to("mps")` is insufficient. [R8][R9]

Recommended porting sequence:

1. Keep a CPU float64 reference for final-token penalties, with a small fixed set of saved logits.
2. Implement a float32 equivalent and compare score differences and selected token IDs, including near ties.
3. Compare device float32 postprocessing with that reference, then evaluate end-to-end output quality.
4. If a required operation remains unsupported, use an explicit measured CPU stage or a compatible implementation. Record transfers and synchronization. Do not hide the issue behind implicit fallback.

Disabling penalties and using parallel argmax is an experiment, not a semantics-preserving speed patch. Code legitimately repeats names, punctuation, and keywords, so prose repetition penalties need their own evaluation. Retain the original decoder path until the alternative meets the agreed quality floor. These are proposed adaptations, not a validated Mac port.

### Hardware-dependent runtime choice

| Target | First NCM implementation | Later option if profiling justifies it |
|---|---|---|
| NVIDIA | Eager PyTorch CUDA reference | Compile fixed stage functions; then consider CUDA graph-compatible paths |
| Apple Silicon | Explicitly port and validate PyTorch MPS operations/dtypes | Custom MLX modules or per-stage Core ML export |
| CPU-only | PyTorch correctness/reference worker; measure interactive viability | Supported CPU kernels and selective quantization; baseline-only mode if NCM misses budget |

MLX LM supports generation, quantization, and fine-tuning of compatible models on Apple Silicon; its converter is not evidence of support for this custom NCM. A port would need the transformer, residual upsampling/convolutions, codebook heads, decoder, masks, and sampling behavior. Core ML documents graph capture and conversion, with limitations around data-dependent tracing. Prefer exporting stage functions while the host retains generation control rather than assuming an entire Python loop converts correctly. Neither port was tested here. [R10][R11]

## 3. Make the model code-capable in two stages

### Stage A: establish source fidelity

Select a case-preserving, reversible text tokenizer and validate its actual configuration. Separate raw text tokenization from the learned VQ tokenizer: passing one round-trip test does not establish the other. Test both on spaces, indentation, tabs, CRLF, Unicode identifiers, literal strings resembling special tokens, long integers, paths, and uncommon APIs. Disable any decoding cleanup that changes source, and explicitly define supported source encodings.

Use released learned tokenizers only as a quick reconstruction probe. If important code symbols fail reconstruction, retrain the representation before spending on a conditional generator. Start with one supported language and short spans. The representation must reconstruct the target span from its full code hierarchy; it must not see a hidden reference target during inference.

The published NCM procedure uses reconstruction cross-entropy and VQ terms, nested dropout, then freezes the tokenizer for generator training. It corrupts conditioning codes while retaining clean labels and weights losses across levels. Reproduce that baseline before adding a code-specific loss. [R12]

For a code adaptation, proposed additions are oversampling rare identifiers/literals and measuring a version with greater weight on those tokens. These are hypotheses requiring ablations, not proven improvements. Track token accuracy, whole-span exact match, exact identifiers, numeric/string literals, and error categories. An aggregate reconstruction percentage is insufficient. A tokenizer that systematically alters case or symbols is a stop condition for that configuration; retraining or another representation is needed.

### Stage B: conditional fill-in-the-middle generation

Construct tuples of `(prefix, suffix, language/task markers, missing span)`. Encode only the target span into clean hierarchy labels. Give the generator the prefix and suffix as conditioning input; build its training inputs from earlier-level reconstructions, with the selected conditioning corruption. Keep representation parameters frozen for this stage, and test that target labels never enter prompt context. The implementation provides code-to-input helpers, but the inspected release does not supply a complete training command. [R13][R1]

Fill-in-the-middle is supported by established autoregressive training research, which rearranges document spans to teach infilling. Applying an analogous conditional dataset to NCM is our proposed adaptation, not a published code-NCM result. Mix cursor-like random boundaries with syntax-derived spans and compare both; using only complete functions may miss real partially typed edits. [R14]

Use deduplicated, properly licensed source with repository/time-separated training and held-out examples. Start with raw code targets. Teacher-generated alternatives can be added later if they improve held-out usefulness after filtering; they add data-generation cost and can amplify teacher errors. Do not assume an autoregressive teacher's weights or token probabilities can be directly copied into NCM's latent codebooks. Likewise, changing learned codebooks changes the generator's prediction space; ordinary small adapters do not remove the need to retrain that interface.

Pick one bounded output length first, for example a proposed 64-token target. Adding 32/64/128-token buckets can follow once trained, matched configurations are available. Upstream schedules are explicit; changing level lengths at deployment is not proof a checkpoint supports the new task or length. Define prompt truncation rules that preserve both nearby prefix and suffix; larger context is another trained-and-tested configuration. [R15]

A new training implementation also needs reproducible data manifests, save/resume of model/optimizer/codebook state, deterministic fixture checks, validation decoding, and checks for NaNs and degenerate codebook utilization. Begin by overfitting a tiny diagnostic dataset to catch alignment and masking errors, then assess held-out data. No training data, teacher, GPU-hours, or monetary budget has been allocated in this research.

## 4. Optimize in an order that preserves interpretability

1. **Measure batch-one stages and cancellation first.** Include input preparation, repeated prompt work, hierarchy generation, reconstruction, final decoding, token selection, IPC, validation, and display. Use device synchronization for isolated GPU timings; host dispatch time alone is incomplete. MPS and CUDA expose explicit synchronization APIs. Do not add a global synchronization after every stage in the shipping path just to simplify timing. [R16][R17]
2. **Remove avoidable work.** Reuse validated masks/buffers for supported shapes; keep device transfers outside level loops where possible. Retain exact source/symbol caches independently of model caches. Decode only the final hierarchy in the normal suggestion path.
3. **Compile stable stage functions where supported.** Both prompt length and current level determine shapes. Fixed prompt buckets and trained target buckets can limit recompilation, with an eager fallback and separate cold-start measurements. PyTorch's `reduce-overhead` mode uses CUDA graphs under particular conditions and may increase memory use; it is not a generic Mac optimization or a guaranteed speedup. [R18]
4. **Quantize selectively after a quality baseline.** Try supported weight-only transformations on ordinary generator linear layers first; keep codebook distances, normalization, and sensitive output computations at an adequately tested precision. TorchAO documents transformations of linear layers, but custom tied heads and buffers need separate treatment. Count the retained tokenizer, buffers, activations, duplicate copies, and runtime overhead. Report memory saved and useful latency together; smaller weights alone do not establish faster batch-one inference. [R19][R7]
5. **Port only a demonstrated bottleneck.** If Python stage dispatch or a specific operation dominates, replace that boundary or operation with MLX/Core ML/native code and require output parity and held-out quality checks. Keep the original PyTorch implementation as the reference.

The existing generator has an optional prefix-cache path, but query-based initial-code generation rejects that option and evaluation leaves it off. Prefix-cache support inside one request is not evidence of validity across arbitrary edits. Do not reuse an autoregressive radix-cache policy for changing bidirectional context without equivalence tests. [R7][R8]

Avoid four attractive distractions in the first implementation: early exit based on fluent intermediate text; grammar masking of latent codes as if they were ordinary tokens; online learning on each keystroke; and a combined NCM drafter plus autoregressive verifier. All could be later research. Standard speculative decoding's unchanged-distribution result relies on its particular sampling/verification procedure; merely checking an NCM-generated block does not establish that property. [R20]

## 5. Suggested implementation sequence and decision gates

These are proposed finite work packages, not a training/evaluation campaign started here. They have no promised completion dates or compute costs.

| Package | Concrete deliverable | Acceptance gate |
|---|---|---|
| 1. Protocol and scheduler | Typed worker messages, capability handshake, fake worker, version/deadline/cancel state machine | Delayed, failed, reordered, oversized, and stale responses cannot block editing or apply stale text |
| 2. Baseline and replay | Small-code-model adapter, pinned FIM fixtures, a replay dataset, timing/resource recorder | Baseline completes valid edit requests; partial-code cases and cancelled requests are counted |
| 3. NCM reference worker | Device/dtype policy, isolated decoder, initial-code accounting, cancellation points | Reference fixtures match the intended eager pipeline; numeric changes are characterized |
| 4. Code representation gate | Raw-tokenizer and learned-tokenizer round-trip report | Critical-symbol failures are surfaced; unsuitable configurations stop before generator training |
| 5. Conditional NCM training | One-language, one-length model plus frozen data/model manifests | Beats trivial copying on a diagnostic set and meets a predeclared held-out quality floor |
| 6. Device optimization | One measured optimization at a time, with parity and quality evidence | Improves the selected product metric without violating memory, quality, or responsiveness requirements |

**Implement packages 1 and 2 first.** Package 3 can then establish reference compatibility, and package 4 determines whether generator adaptation is sensible. Confirm target device, initial language, usable-suggestion latency, memory limit, and training budget before package 5. This recommendation does not require adopting an IDE UI framework today.

For model comparisons, replay the same contexts, cursor edits, output budgets, and background workload at batch size one. Measure cold startup separately from warm completions. Report time to first useful text and to a complete validated suggestion, p50/p95/p99 with sample counts and uncertainty, no-suggestion/timeout/cancellation rates, exact-symbol failures, and parse/type/test outcomes where applicable. Include cancelled work and warm-up/compile costs; successful-completion-only timing can favor a backend that drops harder requests.

In live editing, incomplete syntax is normal. A parser error already present in the buffer should not automatically suppress every candidate. Use edit-range invariants and bounded local checks on the interaction path; run richer diagnostics asynchronously and repository tests in controlled offline evaluation. Parsing success alone does not prove a suggestion is useful or correct.

Compare at equal available context and matched quality floors. Keep rules/classifier baselines for monitoring, and a small code model for generation. Use held-out repositories and later time periods; select thresholds on development/validation data, not the final test set. A static test failure can identify a defect, while user acceptance still needs task-appropriate evaluation.

Before spending on training, record the still-unspecified target hardware and runtime, initial language, supported source encodings, arrival workload, latency and cancellation deadlines, aggregate memory ceiling, licensed data allowance, and finite training/teacher/compute budget. No supplied hardware preference resolves these choices. Data quantity and training duration cannot be inferred from the released checkpoints; choose them through a bounded pilot rather than promising sample efficiency. Budget exhaustion ends that study and produces a report, not an automatic extension.

Make the proposed gates falsifiable in a signed-off experiment manifest before opening the final test set:

- **Interface:** every enumerated malformed-frame, unsupported-bucket, Unicode-range, deadline, duplicate-result, crash, and restart fixture must terminate safely. In particular, edit during inference, cancel, then inject its late response: no stale candidate may display or apply. Burst replay must never exceed the declared scheduler bounds.
- **Representation:** raw-tokenizer fixtures must round-trip exactly. Require zero observed critical-symbol changes on the declared learned-tokenizer validation set, and report whole-span fidelity and sample counts by length and symbol category. This proposed strict gate is unvalidated and proves no universal losslessness; any observed critical corruption stops that configuration before generator training.
- **Numerics:** retain saved-logit fixtures with ties and small margins. Record every float64/float32 or device mismatch and its disposition; do not claim parity while unexplained mismatches remain. Unsupported operations, nonfinite values, and collapsed codebooks stop the affected run.
- **Adoption:** predeclare a quality floor, allowed regression margin, minimum useful benefit, cancellation bound, memory ceiling, sample size, and uncertainty method. These thresholds remain unset until product requirements are supplied. Compare paired held-out tasks at batch one, including errors and dropped requests; report energy only if measured with a documented method. Adopt only if the measured benefit clears the declared threshold while quality and resource bounds pass. Insufficient evidence yields no adoption decision.

If NCM helps multiline spans but loses on short outputs, validate task/length routing on development data before testing it on held-out tasks. If it fails the device or quality gate, retain the shared completion system and baseline. No NCM inference, model training, model export, or IDE benchmark was performed for this recommendation.

## Primary sources and limits

Sources were read as documentation, code, or research claims. No compatibility, throughput, model quality, training recipe, or export was executed. NCM implementation links below pin the inspected revision. Other runtime documentation is versioned where available and should be pinned again for an actual build. The previous architecture report is context, not an independent reproduction. Every proposed design, ordering, gate, and illustrative protocol value above is an engineering recommendation.

- **R1:** [NCM release and task inventory](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/README.md), and [inspected source tree](https://github.com/HazyResearch/ncm/tree/c70274273f489abc73832b2b98584a8483b6b203).
- **R2:** [Publisher model card: Qwen2.5-Coder-1.5B base](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B).
- **R3:** [llama.cpp hardware and inference support](https://github.com/ggml-org/llama.cpp).
- **R4:** [llama.cpp server and infill protocol](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
- **R5:** [Tree-sitter incremental editing](https://tree-sitter.github.io/tree-sitter/using-parsers/3-advanced-parsing.html).
- **R6:** [LSP 3.17 position encodings](https://github.com/microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.17/types/position.md).
- **R7:** [NCM generator, tied heads, generation and cache branches](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py).
- **R8:** [NCM evaluation, CUDA assumptions, and final-token penalties](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_shard.py).
- **R9:** [PyTorch MPS double-precision limits](https://docs.pytorch.org/docs/main/notes/mps.html#double-precision-types). This is main-branch documentation, not a certification of an installed runtime.
- **R10:** [MLX LM compatible-model generation, quantization, and fine-tuning](https://github.com/ml-explore/mlx-lm).
- **R11:** [Apple Core ML PyTorch conversion workflow](https://apple.github.io/coremltools/docs-guides/source/convert-pytorch-workflow.html).
- **R12:** [NCM paper, training objectives, §3.3–3.4](https://arxiv.org/html/2610.14162v1).
- **R13:** [NCM VQ-VAE and code/input helpers](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vqvae.py).
- **R14:** [Efficient Training of Language Models to Fill in the Middle](https://arxiv.org/abs/2207.14255).
- **R15:** [Released XSum hierarchy and context configuration](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/config/eval/xsum.yaml), with [residual quantizer implementation](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/quant.py).
- **R16:** [PyTorch MPS synchronization](https://docs.pytorch.org/docs/2.14/generated/torch.mps.synchronize.html).
- **R17:** [PyTorch CUDA synchronization](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.synchronize.html).
- **R18:** [PyTorch 2.14 compile modes and constraints](https://docs.pytorch.org/docs/2.14/generated/torch.compile.html).
- **R19:** [TorchAO quantization overview](https://docs.pytorch.org/ao/stable/contributing/quantization_overview.html).
- **R20:** [Fast Inference from Transformers via Speculative Decoding](https://proceedings.mlr.press/v202/leviathan23a.html).
