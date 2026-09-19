# Screenshot sources and real agent task exchange

This finite local campaign continues the checkpoint from GitHub run
35458894833, artifact `yado-repository-learning-checkpoint-35458894833-1`.
The downloaded archive SHA-256 is
`525f5fc42eb4eb132b0c8f8389233234762a0b53afa7a7cb687569989e160a22`.
It contains the preserved 1787-event native state, web memory, component executor,
source overlay and inherited birth archive. The operational identity is retained.

The assistant supplies network transport and orchestration. A separate model
agent (`source_tasks`) supplied two structured tasks based on the user-selected
source identities. The host relays these exact task meanings through real
Hivemind v1.17.1 MCP. YADO selects executable compositions and validates them.
This is an actual agent-to-kernel task exchange via a host relay; the kernel does
not launch the model agent, invoke Exa Agent, or converse with repository owners.

The source inventory covers Exa MCP, Ghidra, Hivemind, free-for-dev, Nexus Tools,
Dyad, Hoppscotch, mattpocock/skills, and affaan-m/ECC. The latter is the canonical
redirect target of Everything Claude Code. Actual metadata and README bytes are
saved with hashes. Reading and marker checks do not establish comprehension of
the documents. Native learning uses the disclosed structured tasks, not all
repository source code. Third-party skill instructions are treated as data.

The built-in direct web path reported DNS_RESOLUTION_FAILED in this environment.
A separate host HTTPS transport feeds real public bytes through the existing
`fetch_override` seam, retaining the original failures. Direct Exa MCP POST
returned HTTP 403; the installed Exa connector did return the three requested
pages. Neither event is relabelled as a direct native Exa connection.
The saved transport review checks all 18 observed initial/final metadata and
README URLs against the expected public GitHub hosts. It does not independently
verify resolved IP addresses; network routing is enforced by the managed HTTPS
transport. The adapter's private-network flag means no private destination was
requested, rather than a separate kernel-level DNS proof.

Stages:

1. Restore with the existing `repository-learning-resume-20260919/run.py`
   `restore(checkpoint, output, 35458894833)` function; copy the verified
   `component-evolution` directory and `web-memory.json` into the new output.
2. Run `read_sources.py OUTPUT` with repository runtime dependencies installed.
3. Run `run_native.py --predecessor PREDECESSOR --output OUTPUT --hive HIVE`.
   The pinned CLI SHA is checked before launch. A dedicated tracker is used.
   An interrupted campaign can resume the same tracker and journal with
   `--resume --cycles 3`; already recorded tasks are not submitted twice.
4. Run `finalize.py OUTPUT` after the native and source stages finish. This checks
   reopening both native and component executors and hashes the complete state.

Run scripts from the EVA checkout using its dependency-complete Python runtime.
Use a fresh output directory; do not apply them concurrently to an existing live
kernel. Preserve the original checkpoint. Source overlay restoration intentionally
reinstates its exact pinned runtime bytes before opening the old identity.

Evidence distinguishes external agent tasks, a kernel-selected Hivemind goal,
three endogenous continuation cycles, and twelve fresh component tasks. A task
that fails held-out validation remains in review. The complete campaign status
is not an assertion that every task passed. The router is compared against the
already present router on the same disclosed five-case suite; zero gain is zero.

The scripts do not modify canonical files, merge main, or start a background
service. The durable result is the new checkpoint. Existing runtime grammar and
component implementations remain maintainer-authored; selected native programs
are kernel-generated within that grammar.
