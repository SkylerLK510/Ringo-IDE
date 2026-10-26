# Future NCM training boundary

Placeholder only; no training scripts, data, model dependencies, or weights.

Planned stages:

1. Raw-text and learned-tokenizer reconstruction checks on source code.
2. Representation training if the learned tokenizer fails the fidelity gate.
3. Conditional prefix/suffix generator training with the representation frozen.

Hardware, language, licensed data, and a finite compute budget must be chosen
before implementing a training run. Training stays outside the editor runtime.
See the [implementation research](../../docs/NCM_IMPLEMENTATION_METHODS.md).

For a contributor task, start with the artifact manifest and reconstruction probe
in the [NCM integration guide](../../docs/NCM_INTEGRATION.md), then follow S3/S4
in the [roadmap](../../docs/ROADMAP.md). The fixture demo does not exercise either
tokenizer or establish source reconstruction fidelity.
