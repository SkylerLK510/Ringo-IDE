# Future completion measurement boundary

Placeholder only; no benchmark runner, dataset, generated results, or timing claims.

Planned coverage includes batch-one completion replay, cold/warm latency, memory,
cancelled and stale requests, code fidelity, and held-out quality comparisons.
Model identity, context, output limits, hardware, and measurement methods belong
in a future run manifest. Keep private datasets and run outputs outside this repo.
See the [implementation research](../../docs/NCM_IMPLEMENTATION_METHODS.md).

The offline fixture demo is an integration example, not this benchmark or a real
model baseline. Implement the replay runner as S2 in the
[roadmap](../../docs/ROADMAP.md), after the bounded worker/scheduler contract.
