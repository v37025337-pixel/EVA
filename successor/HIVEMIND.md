# Native synthesis and Hivemind

The existing V2 synthesizer can be explicitly activated in the durable cognitive
loop. Its candidates are selected from training examples, then checked against
validation labels. Old failures remain in history; the autonomous controller can
select a new retry once the additional strategy becomes available.

An implementation upgrade preserves the operational identity and exact journal
prefix while assigning the new source manifest a distinct implementation digest.
Stop active goals and sessions before preparing an upgrade. Keep the predecessor
checkpoint and use a new output directory:

```sh
python -m successor.continuity \
  --parent-manifest /path/to/old/manifest.json \
  --parent-state /path/to/old/kernel.sqlite \
  --output /path/to/new-birth
python -m successor native-synthesis-activate \
  --manifest /path/to/new-birth/manifest.json \
  --state /path/to/new-birth/kernel.sqlite
```

Preparation requires runtime validation on opening the new kernel. Reopening also
checks the immutable predecessor snapshot and upgrade event. Keep all files in
the new birth directory together. Generation journals can retain the operational
identity if their independently pinned component sources have not changed.

[Hivemind](https://github.com/dip497/hivemind) supplies the local issue tracker and
MCP transport. The integration uses its CLI, without requiring the desktop app.
The tested release is v1.17.1, Linux x86_64, binary SHA-256
`32a9f345f1bb69f0bda237449bbd28b8fb6262f1e1b7a13efff7dafe9d5c764d`.
Initialize a dedicated tracker outside the EVA checkout with
`hive init --prefix YADO --no-agentic --json`. Hivemind initialization writes
workspace instruction files, so keep that workspace separate.

Use `hive_create_issue` to create an issue whose entire description is JSON:

```json
{
  "schema": "yado.hivemind.goal.v1",
  "spec": {"domain": "relation", "relation": [[1, 2], [2, 3]], "start": 1},
  "budget": 10,
  "mode": "full"
}
```

Its two acceptance criteria must be exactly:

- `Native kernel validation passed`
- `Result is recorded in the durable kernel journal`

Run one finite processing pass:

```sh
python -m successor.hivemind \
  --manifest /path/to/new-birth/manifest.json \
  --state /path/to/new-birth/kernel.sqlite \
  --tracker-root /path/to/tracker/.hivemind \
  --workspace-id persistent-yado-workspace \
  --issue YADO-1 --hive /path/to/pinned/hive --max-steps 40
```

Retain the workspace ID across restarts. The durable intake link prevents a
transport retry from creating a second goal. Changing an accepted description
requires a new issue. A verified result becomes `done`; a terminal withheld
result becomes `in_review`. Each receipt distinguishes the implementation that
executed the result from the implementation publishing it. Cancellation stops a
pending linked goal even if the description has been removed.

Use one writer per tracker and serialize issue edits with processing. The
upstream tracker does not provide compare-and-swap for concurrent updates. The
bridge accepts typed native goals, not general prose or shell commands. It does
not launch external model agents or enable autonomous writes to other projects.
Activation is an assistant-authored binding of existing mechanisms; it does not
promote the canonical G2 control plane or establish consciousness.

## Runtime evolution through Hivemind

A separate issue contract requests one finite evolution cycle:

```json
{"schema":"yado.hivemind.runtime-evolution.v1","objective":"repair_native_source_failures"}
```

The acceptance criteria must be exactly:

- `Kernel emitted a reusable runtime mechanism`
- `Fresh transfer, memory retention and complete regression passed`
- `Mechanism admitted to durable native cognition`

Run it with `python -m successor.hivemind_evolution` and the same `--manifest`,
`--state`, `--tracker-root`, `--workspace-id`, `--issue`, and `--hive` arguments
as above, plus `--output /path/to/evolution-evidence`. Use the dependency-complete
Python environment used for the repository regression. Keep one writer per
kernel and tracker. A checkpoint from an older implementation requires the
explicit continuity upgrade above before opening it with changed sources.

The kernel chooses an unresolved native-source failure from its journal. For
supported one-variable integer polynomials it infers the smallest fitting degree
(0–3), transplants the pinned `PolynomialCodeLineageGene.fit` AST, and emits a
reusable `synthesize(training)` module. The module computes new coefficients on
every invocation. It contains no labels or hardcoded solution from the triggering
task. The inherited exact fitter and the host-authored adapter are recorded as
separate origins; this is bounded recombination, not invention of the algorithm.

Module bytes are frozen before fresh transfer cases. The runner invokes the
complete repository regression in a separate process, passing the actual frozen
module to its integration test, rechecks retained cognitive results, and runs
both native and full kernel audits. Only successful gates permit a durable
`COG_RUNTIME_ADMIT` event. Normal native cognition can then select the new
strategy; unsupported types, fractional coefficients, insufficient examples,
or degree overflow produce WITHHOLD. Existing failures remain unchanged.

An issue retry reuses the durable proposal and completed gate result. A failed
gate stays in review. Cancellation observed before admission prevents activation.
Interrupted gate attempts remain in separate evidence directories. Use
`RuntimeEvolution(kernel).rollback(proposal_tick)` to revoke a module while
retaining its history. Admission adds a journal-pinned Successor runtime strategy;
it does not alter canonical G2 sources, automatically merge GitHub branches, or
start a permanent background service.
