---
name: e7041-checksum-a-request-sequence
description: "Compute the checksum of one stored request sequence under ECSS-E-ST-70-41C clause 6.21.7 and say whether the body on board is still the body that was uplinked. Use when a sequence has sat in the store between uplink and activation and its integrity must be established: refusing an unknown identifier, reading the stored body in stored order rather than the source the ground still has, refusing an empty or part-loaded body, refusing an algorithm the store does not declare, reporting identifier, length and value, treating a drifted declared checksum as corruption, and changing no sequence state. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-checksum, request-sequence-body-integrity, request-sequence-checksum-report, request-sequence-stored-body-verification."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-checksum-a-request-sequence, request-sequence-checksum, request-sequence-body-integrity, request-sequence-checksum-report, request-sequence-stored-body-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Checksum a Request Sequence (space-systems/ecss/e7041-checksum-a-request-sequence)

Use when the task is the checksum request of ECSS-E-ST-70-41C clause
6.21.7 -- establishing whether one stored request sequence still holds
the body it was given, with the seven normative items that clause
places on the computation and the report.

## Domain quick reference

- A sequence can sit in the store for months between being uplinked
  and being activated, and the store is memory like any other. This
  request is the only routine way to find out whether the body that
  would run is still the body that was sent.
- It reads the stored body, on the stored side, in stored order. Any
  shortcut past that -- checksumming the uplink buffer, the ground
  copy, a cached value -- verifies something that was never in doubt.
- A part-loaded body has no meaningful checksum. Half a sequence
  produces a number that is stable, repeatable and about nothing.
- The algorithm is one the store declares. Substituting another
  silently produces a value that disagrees with the declared checksum
  for a reason that has nothing to do with the body.
- The report carries the length alongside the value. A checksum that
  matches over the wrong number of octets is the failure mode a bare
  value cannot distinguish from success.
- A declared checksum that disagrees with the computed one is a
  corruption finding. Re-reporting the declared value is the specific
  mistake that makes a corruption check confirm itself.
- The computation changes nothing, which is why a sequence can be
  checksummed while the engine is running it -- and why this request
  is safe to issue during an anomaly.

## Workflow

1. Normalize the store and reject a duplicate identifier, a body
   whose request indices are not the stored order, a request carrying
   no octets or an octet outside the single-octet range, an empty slot
   carrying a body, a loaded slot carrying none, or a non-integer
   declared checksum.
2. Refuse an algorithm the store does not declare, and refuse it
   whether or not the named sequence turns out to exist.
3. Resolve the identifier; an absent sequence is a refusal and no
   further state is examined.
4. Refuse a body that is still under load, and refuse an empty one,
   with distinct codes so the ground knows which it was.
5. Flatten the stored body into one run of octets in stored order and
   run the declared algorithm over it.
6. Report the identifier, the request count, the octet count and the
   computed value; never report the declared value in its place.
7. Compare against any declared checksum and close with intact,
   corrupt, or unverified when no declared value exists to compare
   against, leaving every sequence state untouched.

## Pitfalls

- Checksumming the uplink buffer or the ground copy. The result
  agrees with itself and says nothing about the stored body, which is
  the only thing that will actually run.
- Reporting the declared checksum as the computed one. The corruption
  check then passes by construction, for every sequence, forever.
- Treating a missing declared checksum as a pass. There was nothing
  to compare against, and "intact" claims a verification that did not
  happen.
- Checksumming a body still under load. The value is repeatable, so
  it looks like a real measurement, and it describes a body that does
  not exist yet.
- Omitting the octet count from the report. A value that matches over
  a truncated body is then indistinguishable from a clean pass.
- Substituting a different algorithm when the named one is unknown.
  The mismatch that follows sends an operator hunting for corruption
  in a body that is intact.
- Refusing to checksum an executing sequence. The computation changes
  nothing, and the middle of an anomaly is exactly when the ground
  most needs to know whether the body is sound.

## Behavior contract (gate 3)

The store and body normalization, stored-order flattening, the CCITT
cyclic redundancy check against its published check value, the modular
checksum's completing property, algorithm dispatch and refusal, the
unknown, empty and under-load refusals, the length-bearing report, the
intact, corrupt and unverified verdicts and the untouched store are
exercised by the gate 3 contract test:
scripts/test_e7041_checksum_a_request_sequence.py against
scripts/e7041_checksum_a_request_sequence_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_checksum_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
