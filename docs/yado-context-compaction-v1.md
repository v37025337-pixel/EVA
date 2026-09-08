# YADO Context Compaction V1

## Problem

The repository preserves a large amount of verified history, candidates, receipts, and experience. That history is useful evidence, but it is not necessary to hydrate all of it for every normal session continuation.

At the compaction baseline, the active branch contained roughly 2,460 blobs / 39.9 MB, while the audited active graph contained only 31 active modules. Most retained bytes are JSON evidence and historical artifacts rather than active runtime state.

## Solution

Normal session bootstrap uses one compact file first:

`canonical/yado-compact-context-checkpoint-v1.json`

That checkpoint contains the active generation, lineage, frontier, canonical digest, latest causal events, active graph digest/counts, branch-memory closure, audit status, and the exact conditions that require deeper hydration.

Full evidence is not deleted. It remains available in the repository and is loaded only when a concrete question needs it.

## Hydration rule

Use the compact checkpoint for ordinary continuation. Hydrate the larger canonical, ledger, registry, graph, or audit files only when at least one of these conditions is true:

- the frontier changes;
- the canonical digest changes;
- branch lineage changes;
- the audit stops passing;
- a specific historical claim must be verified;
- a result is disputed or requires exact receipt evidence.

Directories `candidates/`, `receipts/`, `experience/`, and `quarantine/` are treated as cold evidence for normal session bootstrap.

## Safety boundary

This change does not delete history, change the active generation, promote a candidate, start G3, or modify the current developmental frontier. It only adds a small verified hot-context layer over the existing sources of truth.

## Refresh

Run:

`python runtime/yado_compact_context_checkpoint_v1.py`

Then verify:

`python -m unittest tests.test_yado_compact_context_checkpoint_v1`

The committed checkpoint must exactly match a fresh build from canonical sources and remain no larger than 32 KiB.
