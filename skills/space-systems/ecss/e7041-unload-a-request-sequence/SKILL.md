---
name: e7041-unload-a-request-sequence
description: "Determine whether an unload of one or more request sequences can proceed under ECSS-E-ST-70-41C clause 6.21.5.4, and what the store looks like afterwards. Use when a command releases held sequences and the space they occupy: failing a name the store does not hold instead of passing it off as a no-op, refusing to pull a sequence out from under a running execution, releasing exactly the space each accepted sequence occupied, freeing the identifier for a later load, refusing a request that names one sequence twice, and deciding a multi-sequence request per name. Trigger: ecss, e-st-70-41-packet-utilization-scope, unload-request-sequence, request-sequencing-service, request-sequence-store-reclaim, executing-sequence-unload-refusal, per-sequence-unload-verdict."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-unload-a-request-sequence, unload-request-sequence, request-sequencing-service, request-sequence-store-reclaim, executing-sequence-unload-refusal, per-sequence-unload-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Unload a Request Sequence (space-systems/ecss/e7041-unload-a-request-sequence)

Use when the task is the unload of
ECSS-E-ST-70-41C clause 6.21.5.4 -- releasing named sequences and the
store space they occupy, with the six normative items that clause
places on accepting each name and on the store that is left.

## Domain quick reference

- An unload is the only way a held identifier becomes free. Every
  later load of that name depends on this one command having been
  accepted, so a silent failure surfaces as a load failure instead.
- Unloading a name the store does not hold is a failure, not a no-op.
  Reporting success makes an operator believe a stale procedure was
  cleared when what was actually cleared was nothing.
- An executing sequence is not unloaded. The block it occupies is
  still being read out request by request, and freeing it hands that
  space to the next load while the procedure is mid-flight.
- An aborted sequence can be unloaded. It stopped, nothing is reading
  it, and leaving it held would strand the space it occupies.
- The space released is the space that sequence occupied and nothing
  more. A store whose free capacity grows by a rounded or nominal
  figure drifts out of step with what it can actually hold.
- The capacity itself never changes. An unload moves space from used
  to free; a store that reports a different capacity afterwards is
  reporting a different store.
- A name given twice is a malformed request. The second release would
  free space that the first already freed and the store would
  over-count its own free capacity.
- A multi-sequence unload is per name. One executing sequence among
  four does not refuse the other three, and the request comes back
  partially accepted with that name reported.

## Workflow

1. Normalize the store: a size and a request count per held
   sequence, a state from the small legal set, and a used total the
   declared capacity can hold.
2. Normalize the request: a bare name, a list or a request object,
   order preserved, and reject an empty request or a repeated name.
3. Decide each name on its own against the store: held at all, and
   in a state that permits the release.
4. Record per name what would be released -- the sequence's own size
   for an accepted name, nothing for a refused one.
5. Sum only the accepted releases, drop exactly those sequences from
   the store, and move that much from used to free with the declared
   capacity untouched.
6. Set the verdict from the split between released and refused names
   and report one finding per refusal.

## Pitfalls

- Answering an unload of an absent sequence with success. The ground
  believes a stale procedure was cleared and it never existed.
- Unloading an executing sequence because the identifier is held.
  The next load is handed space the running procedure is still in.
- Adding a nominal block size back to the free capacity rather than
  the sequence's own size. The store's idea of free drifts from what
  it can hold, and the drift only shows up at the next big load.
- De-duplicating a repeated name instead of refusing the request.
  The free capacity is credited twice for one release.
- Refusing a whole multi-name request because one name is executing.
  The three sequences that could have gone stay held and the next
  load fails for space.
- Changing the declared capacity on an unload. Capacity is a property
  of the store, not of what happens to be in it.

## Behavior contract (gate 3)

The store normalization, the request normalization with its repeated
name refusal, the per-name held and state decision, the exact space
released, the freed identifier and the accepted, partially accepted
or rejected verdict are exercised by the gate 3 contract test:
scripts/test_e7041_unload_a_request_sequence.py against
scripts/e7041_unload_a_request_sequence_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_unload_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
