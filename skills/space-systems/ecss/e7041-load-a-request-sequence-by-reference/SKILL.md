---
name: e7041-load-a-request-sequence-by-reference
description: "Evaluate a load of a request sequence by reference under ECSS-E-ST-70-41C clause 6.21.5.3 and decide whether the store takes it. Use when the command names a source the system already holds instead of carrying the body: resolving the reference to exactly one readable source and refusing a dangling or ambiguous one, grading the resolved content as strictly as an inline body, refusing an identifier the store already holds, sizing the capacity check from the resolved content rather than any size declared beside the reference, and recording on success the source the sequence came from. Trigger: ecss, e-st-70-41-packet-utilization-scope, load-request-sequence-by-reference, request-sequencing-service, dangling-sequence-source-reference, ambiguous-sequence-source-reference, resolved-sequence-content-size."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-load-a-request-sequence-by-reference, load-request-sequence-by-reference, request-sequencing-service, dangling-sequence-source-reference, ambiguous-sequence-source-reference, resolved-sequence-content-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Load a Request Sequence by Reference (space-systems/ecss/e7041-load-a-request-sequence-by-reference)

Use when the task is the load by reference of
ECSS-E-ST-70-41C clause 6.21.5.3 -- a command that names a source the
on-board system already holds rather than carrying the sequence body,
with the six normative items that clause places on resolving that
reference and on accepting what it resolves to.

## Domain quick reference

- The command carries a pointer, not a body. That is what makes it
  small enough to re-send and what moves every acceptance check from
  arrival time to resolution time.
- A dangling reference is a failure, not an empty load. The source
  was expected to be there, and a load that quietly creates nothing
  leaves the ground believing a procedure is armed.
- A reference has to resolve to exactly one source. Picking the first
  or the newest of several applies a rule the ground cannot see, and
  the sequence that runs is not the one anybody chose.
- A source can be present and still unreadable. Resolution is two
  questions -- does it exist, and can it be read out -- and they fail
  for different reasons the ground has to tell apart.
- Resolved content is graded exactly as an inline body would be. The
  indirection changes where the requests came from, never how
  carefully they are checked.
- The capacity check uses the resolved size. A size declared beside
  the reference is a hint from the ground about content it is not
  holding, and sizing the store from it overfills on the first drift.
- The load is all or nothing. A sequence assembled from part of a
  resolved source looks runnable and is not the procedure the source
  describes.
- A loaded sequence records the source it came from. That is what
  lets a later reload, an unload and a direct load of the same
  identifier be told apart in the store.

## Workflow

1. Normalize the load request into a sequence identifier, a
   reference and any size declared alongside it.
2. Normalize the store and note that an already-held identifier is a
   refusal reason, without stopping the rest of the checks.
3. Resolve the reference against the repository: no match, more than
   one match and an unreadable match are three distinct refusals and
   each names itself.
4. Grade the resolved content as a carried body would be graded: at
   least one request, each acceptable standing alone, none targeting
   the sequence being loaded, and the position of every finding kept.
5. Size the resolved content with a header per request and compare
   that, never the declared size, against the free capacity.
6. Apply the load only when nothing was collected, writing the
   origin and the source reference into the store entry; otherwise
   return the store exactly as it arrived with every reason at once.

## Pitfalls

- Treating a dangling reference as an empty load. Nothing is armed
  and the ground has no reason to think so.
- Resolving an ambiguous reference by a tie-break. The load succeeds
  and nobody can say which source ran.
- Trusting the declared size. It describes content the commanding
  side is not holding, and the store overfills the first time the
  source is edited without the command being updated.
- Grading resolved content more loosely than an inline body because
  it was already on board. Being resident is not being valid.
- Dropping the source reference once the load succeeds. A later
  reload cannot then be told from a direct load of the same
  identifier, and the provenance of a running procedure is lost.
- Stopping at the first refusal reason. The ground fixes the
  reference, re-sends, and meets the capacity problem next pass.

## Behavior contract (gate 3)

The repository normalization, the three-way reference resolution,
the resolved-content grading with positions, the resolved-size
capacity fit, the all-or-nothing application and the recorded source
reference are exercised by the gate 3 contract test:
scripts/test_e7041_load_a_request_sequence_by_reference.py against
scripts/e7041_load_a_request_sequence_by_reference_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_load_a_request_sequence_by_reference.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
