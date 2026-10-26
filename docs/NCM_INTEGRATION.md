# NCM integration guide

This is the collaborator implementation map. `NcmBackend` is still a stub.
There is no model download, inference, training command or demonstrated
code-capable NCM checkpoint here. Start with the [offline contract](../README.md).

## Pinned reference and evidence

NCM means Next-Concept Modeling. The inspected upstream revision is
`c70274273f489abc73832b2b98584a8483b6b203`, not a claim about the latest release.
The [architecture research](NCM_ARCHITECTURE_RESEARCH.md) records its audit and
task limitations; the [implementation research](NCM_IMPLEMENTATION_METHODS.md)
describes proposed device ports and experiments. Re-audit if choosing a different
revision. Those documents describe their October 2026 inspections.

| Pinned source | Integration seam |
|---|---|
| [Release README](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/README.md) | Task inventory and paired artifacts |
| [models/next_concept.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py) | Initial codes, hierarchy generation and cache constraints |
| [models/vqvae.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vqvae.py) | Learned representation, cumulative reconstruction, decoder |
| [scripts/eval_shard.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_shard.py) | Reference loading and final token selection |

The generator emits code indices, which require reconstruction and decoding into
ordinary text. Learned codes are neither source tokens nor human-readable
reasoning steps. Both generator and retained representation/decoder matter for
memory and device placement. Released task weights do not establish code infill.

## Adapter stages to implement

Work behind [NcmBackend](../src/ringo_ide/workers/ncm/backend.py), preserving the
shared [CompletionBackend](../src/ringo_ide/workers/base.py) interface. This is a
proposed stage breakdown, not an implemented tensor API:

| Stage | Input → output | Required evidence |
|---|---|---|
| Load | Artifact manifest → eager components | Strict checkpoint/config match; device/dtype validation; eval/no-grad |
| Encode | Prefix/suffix/task/language → conditioning | Pinned format/tokenizer; bounded context; target never leaks into prompt |
| Generate | Conditioning → initial/finer codes | Account for initial pass and every level; saved fixtures |
| Reconstruct | Codes → cumulative latent representation | Match reference codebooks, upsampling and residual path |
| Decode | Final reconstruction → logits → tokens → text | Reference token selection/EOS; exact-symbol tests |
| Return | Candidate → complete or terminal result | Same identity; supported limits; cancellation/deadline checks |
| Close | Loaded instance → released resources | Explicit cleanup and safe worker restart |

Keep stages independently testable. Extract inference from the evaluation script
instead of importing its top-level dataset/CLI execution. One inference executor
owns the model. Add cancellation/deadline checks before generation, between
levels, before decoding and before emitting. Adapting the loop is needed for
internal checks; wrapping a blocking call only discards final output. Do not
promise immediate kernel cancellation or stream intermediate refinements as
stable text. Output buckets must match trained schedules, not demo values.

## First ML contribution: artifact manifest

Implement a public template/schema, keeping private paths and run data outside
the repository. Record source/adapter revisions; generator and learned-tokenizer
checkpoint hashes; base text-tokenizer revision and normalization; full config
hash and hierarchy lengths; context/output limits; device/runtime versions;
compute/postprocessing dtypes; seed/sampling/EOS policy; licenses; loaded
parameter count and measured peak memory. Reject incompatible artifacts instead
of silently accepting partial state. Preserve stage fixtures for comparison.

## Code capability gates

These are proposed experiments; no training runs are launched by this scaffold.

1. Probe ordinary text-tokenizer and learned VQ round trips separately on case,
   identifiers, numbers, indentation, tabs, CRLF, Unicode, paths and literals.
   Report byte/span/critical-symbol errors separately. Passing raw tokenization
   does not establish learned reconstruction fidelity.
2. If critical symbols corrupt, stop that configuration and train or choose a
   suitable representation before spending on a generator.
3. Freeze the selected representation, then train prefix/suffix → missing span
   generation. Changing codebooks changes the generator label space. Installing
   research weights alone does not teach the task.
4. Begin with one agreed language/output bucket, licensed data separated by
   repository/time, saved fixtures and finite compute budgets.
5. Compare against a real small code-model baseline at batch one with equal
   context and declared quality/resource thresholds.

See the [training boundary](../research/ncm_training/README.md) and
[roadmap](ROADMAP.md) for dependencies and completion criteria.

## Device validation and adoption

The implementation research identified CUDA assumptions and float64
postprocessing requiring attention for MPS. Port generator, retained tokenizer
and temporary tensors together. Keep a CPU numerical reference and saved logits
with near ties; characterize changed selected tokens. CPU correctness does not
establish interactive performance. No MLX/llama.cpp NCM loader is supplied here.

Keep an eager reference before compilation/quantization. Measure startup,
encoding, hierarchy work, reconstruction, decoding, validation and delivery,
including discarded/cancelled work. Define quality floor, memory ceiling,
cancellation bound, useful benefit and uncertainty method before held-out
comparisons. Retain the ordinary baseline if NCM fails those gates. The
[benchmark boundary](../benchmarks/completion/README.md) remains future work.
