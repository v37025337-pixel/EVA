# Genetic components in the main kernel

`SuccessorKernel` now uses the existing `GenerationKernel` selection and admission
algorithms through an adapter over its own causal journal. There is one SQLite
state for cognitive goals, learned programs, component selection, activation,
queued tasks and rollback. No separate generation process or database is needed
for this path. The older standalone generation interface remains compatible.

```bash
python -m successor component-propose --manifest /path/to/manifest.json --state /path/to/kernel.sqlite
python -m successor component-admit --manifest /path/to/manifest.json --state /path/to/kernel.sqlite
python -m successor component-status --manifest /path/to/manifest.json --state /path/to/kernel.sqlite
python -m successor run --manifest /path/to/manifest.json --state /path/to/kernel.sqlite --input task.json
```

Proposal retrieves inherited gene expressions and freezes a measured profile.
Admission evaluates that frozen profile on fresh cases and regression cases,
including retained cognitive memory from the component birth checkpoint. A
failed admission cannot activate it. Admission and activation are atomic in the
main journal. Existing learned native programs remain available to cognition.

The ordinary `run`, `submit` and `resume` interfaces accept a typed component task:

```json
{
  "kind": "component",
  "payload": {
    "organ": "THINKING",
    "current": 0.1,
    "target": 0.8,
    "budget": 2,
    "stages": [
      {"stage_id": "slow", "cost": 1, "expected_gain": 0.75, "latency": 9},
      {"stage_id": "fast", "cost": 1, "expected_gain": 0.75, "latency": 1}
    ]
  },
  "expect": {"path": ["answer"], "equals": "fast"}
}
```

The component contract in `successor.generation.execute_component` supports
`LOGIC` (Boolean rule fitting), `THINKING` (planning), `INTELLIGENCE` (capability
routing) and `CODE` (program repair/synthesis). Expected query answers stay in
the outer verifier and are not passed to the component. Legacy relation/event
task contracts are preserved; they are not Boolean-training or planning tasks.

Every execution records the active profile and its causal event. The main
verifier recomputes component outputs and checks the main result's link to that
event. Task retry identity includes the profile, so a previous failure can be
retried after a verified genetic change without rewriting the old failure.

`component-rollback` restores parent dispatch while retaining the journal. Use
the existing continuity procedure to carry an older kernel state to a new
implementation; a fresh manifest does not migrate an existing identity. This
adapter does not import or relabel an older standalone generation journal.

For the reviewed `GENOME_FITNESS_BINDING_MAINTENANCE_V1` source transition,
continuity appends a component `SOURCE_UPGRADE` bound to the new implementation
event. Historical source pins and events remain intact. Only the exact reviewed
predecessor and genome SHA are accepted. Component execution then requires a
fresh measurement of the inherited profile, protected tasks and cognitive memory:

```bash
python -m successor component-readmit --manifest /path/to/upgraded/manifest.json --state /path/to/upgraded/kernel.sqlite
```

The copied checkpoint can be inspected before readmission. Historical admission
labels cannot authorize execution under the changed source.

The connection was implemented by the assistant. The existing kernel selects
the gene profile and generates individual program candidates. This remains the
existing bounded component grammar and one activation/rollback lifecycle; it
does not establish unrestricted self-rewriting or general intelligence.
