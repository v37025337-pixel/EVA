# Native program development

YADO can select executable compositions from a versioned library of reviewed
operations. The maintainer implements the language, search and checks; the kernel
selects each program using training examples. This is bounded native synthesis,
not unrestricted Python generation or evidence of general intelligence.

The path connects existing layers:

1. A typed task enters the durable cognitive journal.
2. The controller chooses an available strategy using its measured self-model.
3. The generator searches expressions and infers output structures from training
   examples, without validation labels or query answers.
4. The executor validates the program representation and exact emitted source.
5. Frozen code runs on independent held-out examples. Verified programs enter
   memory; failures remain failures and update the self-model.
6. Later synthesis can inline verified programs, recording the parent source
   hashes. The development controller chooses retries from recorded deficits.

## Run

Install the repository's existing runtime and Successor requirements, then:

```bash
python -m successor build --output successor/state/program-birth
python -m successor compositional-synthesis-activate --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite
python -m successor goal --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite --input successor/examples/structured-program-goal.json --budget 10
python -m successor think --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite --max-steps 100
python -m successor program-status --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite
```

For previously failed goals, `program-develop` activates the new route and lets
the existing controller select and execute bounded retry sessions:

```bash
python -m successor program-develop --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite --rounds 3
```

This command ends after its finite budget. It is not a background service.

## Data and compatibility

Legacy `native_source` goals keep their original scalar contract. The additive
`yado.native_program_goal.v1` schema supports named JSON inputs and JSON outputs:
strings, integers, booleans, nulls, lists and objects. Bounds on examples, depth,
nodes and text are validated before execution. Query answers are not accepted.

The new strategy is `native_compositional_v1`, activated by a separate journal
event. Historical generator implementations and activation records are retained.
Use `successor.continuity` with an exact source-update map to migrate an existing
pinned binary state; creating a fresh birth does not migrate the old identity.

Generated Python calls reviewed helper globals. Execute it through
`yado_active_native_learning_v1.execute_source(candidate, inputs)` or the kernel;
do not treat its source hash alone as permission to execute supplied Python.
Unknown schemas and source/representation mismatches are rejected. New execution
records are recomputed during verification and replay, including query outputs.

## Scope and rollback

The operator library supports text, structured data, numeric expressions, Python
AST inspection and unified diff construction. These library operations were
implemented by the maintainer. Kernel-selected compositions and memory reuse do
not amount to invention of the underlying JSON parser or diff algorithm.

```bash
python -m successor compositional-synthesis-deactivate --manifest successor/state/program-birth/manifest.json --state successor/state/program.sqlite
```

Deactivation stops new compositional synthesis. It preserves the journal and
verified source memory. Implementation rollback uses the predecessor checkout,
manifest and state preserved by the continuity procedure.

This release does not grant new credentials, start external agent conversations,
or deploy itself. External actions still require actual configured tools and the
user's authorization. Programs remain constrained by the available operators and
search budget; unsupported tasks end with WITHHOLD.
