---
name: e5053-reserved-field
description: "Evaluate the reserved octet that a packet transfer protocol data unit carries between its protocol identifier and its user application field. Use when an ECSS-E-ST-50-53C clause 5.3.4 link has to settle sender duty and receiver tolerance: write the held-back pattern on transmission, fix the octet offset from the path length, read it back from a received unit, and apply a stated receiver policy that either discards a deviant octet, accepts it and records the deviation, or accepts it silently, which is itself reported. Tally a run of received octets into accepted, discarded and deviation counts. Refuses an unknown role, an unknown policy and an empty log. Trigger: ecss, e-st-50-53c, spacewire-reserved-field, reserved-octet-pattern, receiver-tolerance-policy, reserved-field-offset, protocol-revision-boundary."
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
  tags: [ecss, e-st-50-53-packet-transfer-scope, e5053-reserved-field, spacewire-reserved-field, reserved-octet-pattern, receiver-tolerance-policy, reserved-field-offset, protocol-revision-boundary, reserved-deviation-log]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Transfer — Reserved Field (space-systems/ecss/e5053-reserved-field)

Use when the task is the reserved octet of ECSS-E-ST-50-53C clause 5.3.4
-- what a sender is obliged to write there, and what a receiver is
entitled to do with what it finds.

## Domain quick reference

- One octet between the protocol identifier and the user application
  field is held back for a later revision of the protocol. It carries no
  information today and is not spare space for an implementer.
- The sender has no choice. It writes the held-back pattern, and any
  other value is a sender defect to be rewritten before transmission
  rather than a property of the link.
- The receiver has a policy choice, and it is a real engineering
  decision rather than a detail: discard a unit whose reserved octet is
  not the held-back pattern, accept it and record the deviation, or
  accept it silently.
- Discarding is the safe reading today and the first thing that breaks
  the day a peer starts using the octet under a later revision.
  Recording keeps the link alive across that boundary and leaves the
  evidence that explains it.
- Accepting silently is the one policy with no recovery path. Nothing in
  the log distinguishes a non-conformant sender from a peer that has
  moved to a newer revision, so the policy itself is reported as a
  finding.
- The offset is not fixed. Path-address bytes precede the target address
  and shift every field after it, so the reserved octet sits at the path
  length plus two.
- A run of received octets is worth tallying rather than judging one at
  a time: a scattered deviation reads as corruption, a steady one reads
  as a peer on a different revision.

## Workflow

1. On transmission, write the held-back pattern into the single reserved
   octet. Treat any other value in a unit about to be sent as a defect
   to be fixed, not as a case to be graded.
2. Fix the reserved octet offset from the number of path-address bytes
   the unit carries, and refuse a negative or non-integer path length.
3. On reception, check the unit is long enough to hold the field, then
   read the octet at that offset.
4. Grade the octet: it either carries the held-back pattern or it does
   not, and a deviation is recorded as either a non-conformant sender or
   a peer on a later revision, because the octet alone cannot separate
   them.
5. Apply the stated receiver policy to get a disposition, and report a
   silent-accept policy as a finding in its own right.
6. Where a run of units is available, tally accepted, discarded and
   recorded counts and the positions of the deviations, so a scattered
   pattern can be told from a steady one.

## Pitfalls

- Using the reserved octet for a project-local flag. It is held for a
  later revision of the protocol, so the flag works until the peer is
  upgraded and then collides with a meaning that is not yours.
- Reading the octet at a fixed offset. Path-address bytes move it, so a
  hard-coded position reads the user application field on every
  path-routed unit.
- Accepting a deviant octet silently. The link keeps working and the one
  piece of evidence that would have explained a later failure is never
  written down.
- Discarding on a deviation with no policy declared. Both dispositions
  are defensible, but only a declared one is reviewable, and an
  undeclared discard looks like a link fault.
- Judging a single deviation. One deviant octet among many is corruption
  and a steady one is a revision boundary; the tally over a run is what
  separates the two.

## Behavior contract (gate 3)

The sender encoding, offset computation, octet read-back, policy
dispositions and log tally are exercised by the gate 3 contract test:
scripts/test_e5053_reserved_field.py against
scripts/e5053_reserved_field_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_reserved_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
