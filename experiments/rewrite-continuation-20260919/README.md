# Current-parent continuation repair

See `docs/yado-current-parent-rewrite-continuation.md` for the gate contract.
The committed-experience receipt records the actual current maintenance parent,
three executed variants, seven diagnostic priorities and zero selection changes.
The honest result is WITHHOLD, not a new active generation.

Continue the previously sealed tick-2001 checkpoint with:

```bash
python experiments/rewrite-continuation-20260919/run_memory.py \
  --predecessor /absolute/path/next-step-checkpoint \
  --output /absolute/path/new-checkpoint
```

The harness checks the complete predecessor receipt, explicitly versions the
changed generator CLI source, preserves the operational identity and journal
prefix, invokes public development and two endogenous autonomy cycles, then lets
the existing lineage selector attempt its next step. No goal or candidate is
injected. A lineage WITHHOLD remains a WITHHOLD. The component state is unchanged.
The adapter and observation harness are assistant-authored maintenance.
