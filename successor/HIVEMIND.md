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
