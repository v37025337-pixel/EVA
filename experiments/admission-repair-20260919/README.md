# Versioned admission repair

Two defects blocked continuation of the saved native tick-1856 checkpoint:
historical library retention repeated live PyPI discovery, and V1 compositional
equality observed dictionary insertion order. The original JSON goal also
contained confounded training examples: a lowercase-string predicate fitted
its training labels but failed validation.

`successor/generation.py` now verifies the frozen library candidate and stored
PyPI proof during historical retention. New library discovery keeps its live
verification path. Stored failures remain failures; changed proof bytes fail
replay.

V2 adds explicit `json_equal_v2` and `json_not_equal_v2` primitives. Object keys
are unordered, arrays remain ordered, and booleans differ from integers. V1
search, emitted programs and statistics remain reproducible. The bounded JSON
domain still excludes floats and lone surrogate code points. This is not a
claim of complete JSON standard support.

Migration copies both journals. The native `IMPLEMENTATION_UPGRADE` and component
`SOURCE_UPGRADE` bind the new source bytes while preserving the previous events
and pins. Only the explicitly reviewed component predecessor is accepted.
Component execution stays blocked until a fresh `READMISSION` rechecks the
frozen profile and all memory through the new native boundary.

The canonical integrity manifest also pins these four successor modules.
`prepare_binding.py` rebinds exactly their reviewed hashes and appends maintenance
event 317, preserving the ledger prefix and formal generation. The code change
initially tripped that guard; the binding commit restores it. A completed local
checkpoint from before this metadata binding is carried forward one native event
by `seal_binding.py`, with the same component admission and logical identity.

Run from the repository with the checkpoint's existing runtime source overlay
applied, then the reviewed successor implementation from this PR:

```bash
python3 experiments/admission-repair-20260919/run.py \
  --predecessor /absolute/path/to/tick-1856-checkpoint \
  --output /absolute/path/to/new-checkpoint
python3 experiments/admission-repair-20260919/verify.py /absolute/path/to/new-checkpoint
```

The output must be new. The predecessor is never rewritten. No network access
is needed: both live library accessors are blocked and counted. The checkpoint
contains the archived internet sources and prior observations.

The new JSON goal uses six disclosed contract examples and four separate
validation examples, with memory disabled for program selection. Thirty-two
additional labeled cases are generated after source freeze. Old goal 1796
remains WITHHOLD; applying the new source to its two old validation cases is
reported only as regression coverage. Fresh component challenges use another
seed after restart. Measurements are in `observed-results.json` and the complete
checkpoint receipts.

The repair and training contract are assistant-authored. YADO selects the
program and measures the frozen component profile. This does not establish
autonomous architecture invention, G3, general intelligence gain, or an ongoing
background service.
