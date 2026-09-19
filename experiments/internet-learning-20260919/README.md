# Real internet data continuation

This finite experiment continues the preserved native YADO identity from tick
1840, produced by `screenshot-learning-20260919`. It does not reset experience,
alter pinned core sources, merge main, or create a background service.

The user selected Hoppscotch, SecLists, HackTricks and PayloadsAllTheThings.
`sources.py` obtains real repository metadata, a commit SHA, README and selected
JSON/encoding documents. Every document URL is pinned to the observed commit and
its exact bytes are hashed. Sources are data, never executable instructions.

Real GET and POST calls go to the public Hoppscotch demonstration echo root.
Only harmless, freshly generated lesson labels are sent there. Security corpus
strings are local serialization inputs. No corpus payload is sent to a service,
no target discovery occurs, and none of the fetched source code is executed.

## What the kernel does

The assistant authors two example-based goals and relays them through the actual
Hivemind MCP. An independent model agent reviews boundary cases. YADO selects and
emits code using its existing compositional grammar, validates held-out examples,
and retains admitted source in its durable cognitive journal.

- JSON string serialization: exact ASCII JSON representation and string recovery.
  Corpus lines/snippets come from three source projects; Unicode/control cases
  supplied by the assistant/agent are separately marked. Frozen source is tested
  on further strings from the same documents. V8 `JSON.parse` independently
  checks recovery, including the explicitly authored boundary cases at restart.
- Echo extraction: the host removes routing/signature headers, then passes a JSON
  text containing the real method, args, body and path. The learned program must
  parse this text itself and extract method and body. Expected values come from
  the actual request, not from the program being evaluated. Held-out and fresh
  inputs change key order and add nested decoy keys. Fresh HTTP responses are
  requested only after candidate source has been selected and recorded.

The prior normalizer from goal 1788 is also reapplied unchanged to the four new
real repository metadata records. This measures reuse of an earlier result.

## Procedure

Use an isolated EVA checkout at the same source implementation and restore the
exact previous checkpoint overlay. Verify every predecessor receipt hash and
copy its complete state to a separate output. Preserve previous top-level summary
and receipt under `prior-receipts/`; only one writer may open the new state.

1. `sources.py OUTPUT/internet-lesson`
2. `run.py --output OUTPUT --predecessor PREDECESSOR --hive HIVE`
3. `verify.py OUTPUT --predecessor PREDECESSOR`

Run with repository dependencies available. The Hivemind executable is pinned by
SHA-256. Raw echo headers can contain transport metadata; raw bytes belong only
in the user's private checkpoint and must not be committed to Git. Published
`observed-results.json` contains measurements, source URLs and code hashes only.

## Interpretation

This tests narrow data transformations and their use on real observations.
Selecting a provided JSON encoder is not inventing a serializer. Downloading
HackTricks does not establish semantic understanding of it. Held-out strings
from the same documents are not a new-source generalization benchmark.

Negative response probes are separate from successful ordinary extraction cases.
In particular, a program can correctly extract a wrongly typed method without
validating the API schema. Such a result remains a limitation, not a security
success. Inherited JSON equality and component historical-PyPI-replay defects
are not repaired by this experiment. The preserved component executor remains
withheld; successful native restart must not be labelled a component restart.
