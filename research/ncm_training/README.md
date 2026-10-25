# Future NCM training boundary

Placeholder only; no training scripts, data, model dependencies, or weights.

Planned stages:

1. Raw-text and learned-tokenizer reconstruction checks on source code.
2. Representation training if the learned tokenizer fails the fidelity gate.
3. Conditional prefix/suffix generator training with the representation frozen.

Hardware, language, licensed data, and a finite compute budget must be chosen
before implementing a training run. Training stays outside the editor runtime.
See the [implementation research](../../docs/NCM_IMPLEMENTATION_METHODS.md).
