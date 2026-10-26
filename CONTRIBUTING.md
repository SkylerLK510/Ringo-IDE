# Contributing

Start with the [README](README.md), run the demo/tests, and choose one bounded
[roadmap task](docs/ROADMAP.md). Backend stubs are intentional boundaries; do
not replace them with plausible-looking model output.

## Local workflow

From the repository root, with Python 3.11+:

```sh
PYTHONPATH=src python3 -m ringo_ide demo
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
git diff --check
```

Alternatively use an editable virtual-environment install and omit `PYTHONPATH`.
CI installs the package and checks tests/demo on Python 3.11, 3.12 and 3.13.
Packaging changes should verify installed commands outside the source checkout.

While [scaffold PR #1](https://github.com/SkylerLK510/Ringo-IDE/pull/1) is open,
coordinate against `codex/ncm-worker-scaffold`; after merge use `main`.
Create a branch from the agreed integration branch and keep each PR bounded.

## Invariants

- Preserve source snapshots and host-selected ranges. Never apply stale results,
  derive offsets from model output, or normalize untouched bytes.
- Keep monitoring separate from generation and NCM behind the common contract.
- Keep imports inert; future model libraries require optional installation and
  explicit startup, not import-time loading or network access.
- Test asynchronous behavior with controlled clocks/fixtures, not timing sleeps
  or mandatory GPUs. Real-model checks need separate pinned manifests.
- Reserve worker-facing stdout for JSON/protocol data; send logs to stderr.
- Keep private source, weights, data, logs and authentication outside the repo;
  preserve external asset licenses/revisions.

## Pull requests

Explain concrete behavior, the implemented/planned boundary, roadmap task,
checks and remaining limitations. Add request fixtures where useful. Update the
README status table when a stub becomes operational. Model changes need artifact
pins and measured evidence; published speedups are not scaffold results.

The maintainer uses the separate Ringo executable harness for substantive
code/design assessment. Contributors do not need a Codex skill or runtime
package dependency for it. Assessment supplements project checks and human
review; it cannot validate unexecuted model behavior. Training, evaluation and
improvement campaigns do not start automatically from this workflow.
