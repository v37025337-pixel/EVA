# Current-parent rewrite continuation

The V4 reproduction remains a historical proof against the V3 candidate. It
must not serve as the next-generation controller: its parent hash and expected
effects on two named sources refer to that historical transition.

The ordinary generator command now verifies the currently active implementation:

```bash
python runtime/yado_native_self_rewrite_v4_fresh_experience.py \
  --output /absolute/path/new-attempt
```

An optional `--experience /path/to/experience.json` selects an existing sealed
experience document. Its digest, producer controller, outcome consistency,
catalog membership, facts and read-only policy are checked before synthesis.
These checks establish content integrity and controller compatibility; they do
not independently prove that a supplied document came from a real network run.
The CI flow therefore also verifies the complete freshly collected learning
receipt and generated recall artifact with `verified_learning_outputs`.

Each attempt verifies the complete canonical source manifest and uses the exact
active controller bytes. The inherited AST generator may update only the literal
learned-evidence binding. Parent, emitted candidate and candidate with its parent
binding restored are run in three separate restricted processes. The probe has
CPU, memory and wall-clock bounds and rejects network, process and file-write
side effects through Python audit hooks. It is not a sandbox for arbitrary code.
Structural equivalence is required before execution.

The diagnostic uses the actual experience priority and every catalog row's tags.
It records scores and the ordered selection within the existing source budget.
No named source or historical generation must improve. An unchanged selection
returns `WITHHOLD / NO_OBSERVABLE_SELECTION_CHANGE`, including cases where only
the receipt digest changes. A changed selection returns
`READY_FOR_INDEPENDENT_EVALUATION`, never active admission or capability gain.
The priorities are catalog-derived diagnostics, not blind evaluation data.

Every output directory must be new. Failed attempts are retained and cannot
overwrite a positive receipt. Historical V4 candidate/admission paths and active
sources are not written. The old historical CLI is explicit: `--historical-v4`.
`build_committed()` continues to reproduce its original historical evidence.
It locates the original experience by the sealed V4 digest in reachable Git
history, verifies that document's content digest and requires exact reproduction
of the persisted candidate bytes. A later learning receipt cannot silently
replace the historical input. Missing history or mismatched bytes fail closed.

The fresh-learning CI workflow collects public data on its runner, checks the
whole learning receipt, performs this continuation and uploads all evidence.
Its permissions are read-only. A healthy WITHHOLD passes the *controller contract*
check; it does not count as a successful rewrite. Other rejections fail CI.
This specific workflow is registered in the exact active-workflow inventory with
a read-only diagnostic role; it is absent from the write-authorized inventory.

This adapter and its tests are authored by the assistant under user direction.
It reuses the existing bounded synthesis policy. Blind utility, negative transfer,
full candidate regression and admission are still required after a useful
candidate is found; this adapter cannot claim or perform those stages.
G3 and open-ended algorithm invention remain unestablished.
