# Public V2 profile continuation

After the JSON V2 repair, `develop_native_programs()` still called the public
activation entry point with an implicit V1 request. A saved V2 state consequently
raised `COMPOSITIONAL_PROFILE_REQUIRES_DEACTIVATION`. The status endpoint also
returned the V1 catalog and omitted the V2 program: five programs instead of six.

An omitted grammar now preserves the currently active profile. Explicit grammar
changes retain the existing deactivation requirement. The public kernel wrapper
accepts the version argument, and status uses the active grammar for both its
catalog and verified memory. Existing V1 defaults remain unchanged.

Three public integration tests reproduce and verify the repair, including restart
and the rejection of an explicit incompatible profile switch. `bind.py` updates
only the two reviewed module hashes and appends maintenance event 318; it does not
promote a generation or change the admission thresholds.

Run from this source version using the sealed tick-1866 checkpoint:

```bash
python experiments/profile-continuation-20260919/run.py \
  --predecessor /absolute/path/to/admission-repair-checkpoint \
  --output /absolute/path/to/new-checkpoint
```

The output must be new. The predecessor and its complete native/component journal
prefixes are preserved. The run uses the public development method, ten endogenous
goals, a full retained-memory replay and twelve fresh component tasks after reopen.
Both live PyPI accessors are disabled and counted: this is execution on retained
experience, with no new internet-data collection. Source/manifest migration is
explicit and the original operational identity is retained.

The assistant authored the repair and harness. Existing YADO algorithms select
goals and programs within their supported grammar. The results do not establish
G3, consciousness or an ongoing background process. Measured evidence is saved in
the output checkpoint; an assertion failure is never reported as a passed run.

The completed run passed 10/10 endogenous goals, retained all 214 goal records,
and passed 12/12 component tasks after reopening. All 1,866 native and 30 component
predecessor events are preserved; the native journal ends at tick 1968 and the
component journal at 42 events. The public development session selects the old
JSON failure and successfully reuses its learned solution. Program count stays
six. Full regression passes 665/665 with no failures, errors or skips.

`finalize.py` verified the completed state in a separate process, checked the
regression source hashes and sealed ordinary JSON summary/receipt metadata for
checkpoint consumers. It also exports the report referenced by maintenance event
318. Nine regenerated shadow outputs are retained as experiment evidence outside
the active source overlay; they are not admitted. The regression source-unchanged
claim is limited to its enumerated working-code/configuration paths, which exclude
`candidates`. See `observed-results.json` for the measured results.
