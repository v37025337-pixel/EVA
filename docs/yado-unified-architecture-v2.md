# YADO Unified Architecture V2

This architecture repairs a continuity problem: repository history, formal kernel generation,
runtime self-rewrite generations, experience memory and verification were being described as
if they were one version axis. They are now separate planes with explicit bindings.

## Planes

1. Identity and lineage - the formal canonical head and append-only causal ledger.
2. Cognitive runtime - the currently active capability versions used by the unified core.
3. Runtime evolution - physically promoted runtime mutations such as the verified V4 rewrite.
4. Memory and experience - curated historical evidence. This registry is not a live Git branch list.
5. Verification and admission - repository reconciliation, canonical guard, Full Kernel Audit V2,
   complete Successor regression, then admit or roll back.

## Version rule

A capability family may have many historical versions, but only one is active. Older versions remain
only for rollback, regression and provenance. A physical runtime change may not remain paired with a
PENDING promotion receipt.

Formal architecture generation and runtime rewrite generation are intentionally independent:
G2_CANDIDATE_TRCG_V1 can remain the formal architecture while the bounded autonomous-learning
runtime advances to V4. A future architecture generation requires its own admission evidence.

## Development continuity

Every admitted step must preserve this chain:

measured deficit -> target selected from current state -> materialized change -> fresh test ->
full regression -> full audit -> admit/rollback -> next deficit derived from the admitted state.

A new branch, PR, audit or infrastructure repair is not counted as a new development generation
unless it closes that whole chain.

## Branch rule

main is the only active integration line. Other branches are historical or work in progress.
The reconciliation gate fetches the full remote topology and fails when another branch still
retains commits ahead of main, excluding the PR branch currently being tested.

## Claim boundary

This is a software-architecture and lineage reconciliation. It does not establish G3 or subjective consciousness.
