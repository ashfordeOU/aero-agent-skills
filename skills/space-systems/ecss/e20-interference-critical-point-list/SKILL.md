---
name: e20-interference-critical-point-list
description: "Use when derive and submit for customer approval the list of points at which electromagnetic interference margin is demonstrated, as ECSS-E-ST-20C clause 6.3.1.2 requires: select a candidate point for every safety-critical and mission-critical victim circuit on each distinct coupling path, validate each point's frequency band and mandatory record fields, merge the point bands to expose any uncovered stretch of the project's electromagnetic spectrum span, and track whether the assembled list reached the customer and carries a dated approval. Trigger: ecss, e-st-20-electrical-scope, interference-critical-point-list, emi-margin-demonstration-point, coupling-path-selection, frequency-band-coverage-gap, customer-approval-record, emc-critical-point-submission."
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
  tags: [ecss, e-st-20-electrical-scope, e20-interference-critical-point-list, interference-critical-point-list, emi-margin-demonstration-point, coupling-path-selection, frequency-band-coverage-gap, customer-approval-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Interference Critical Point List (space-systems/ecss/e20-interference-critical-point-list)

Use when the task is the clause 6.3.1.2 deliverable of ECSS-E-ST-20C --
assembling the list of points at which the electromagnetic interference
margin is to be demonstrated, and putting that list to the customer for
approval before the demonstration effort is committed.

## Domain quick reference

- The deliverable is a list, not a result. Its purpose is agreement in
  advance on where the margin will be shown, so the customer and the
  supplier commit to the same set of points before any measurement or
  analysis is paid for. A list that was never submitted, or that is
  still awaiting a signature, leaves every downstream demonstration at
  risk of being rejected as evidence against a point nobody agreed to.
- A point is addressed by a victim circuit and a coupling-path family,
  not by a named path. Conducted emission and conducted susceptibility
  belong to the same conducted family, and radiated emission and
  radiated susceptibility to the same radiated family, so an emission
  point and a susceptibility point on the same family are the same
  selection slot filled twice, not two slots.
- The four families are conducted, radiated, common impedance and
  electrostatic discharge. Selection follows criticality: the safety
  group takes a point on every family; the mission group takes the
  conducted, radiated and common-impedance families, and the discharge
  family only where the circuit is externally exposed; the essential
  group takes the conducted and radiated families; the non essential
  group takes none.
- Each listed point carries a fixed record: an identifier, the victim
  circuit, the coupling path, the frequency band in hertz, the
  demonstration method, the required margin in decibels and the party
  responsible. A field left blank is a finding in the list, not a
  detail to fill in during the campaign, because it is exactly what
  the customer is being asked to agree to.
- The demonstration method sets the class of evidence the point will
  produce: a measurement, a coupling calculation, a heritage argument
  from a qualified unit, or a workmanship check on the routing. The
  class is part of what is approved, since a point the supplier
  intends to close by heritage is a different commitment from one it
  intends to close by measurement.
- The listed bands are merged and compared against the project's
  spectrum span. An uncovered stretch means the list leaves a region of
  the spectrum with no point at all, which is a coverage defect in the
  deliverable rather than a result that came out badly.

## Workflow

1. Derive the candidate points: for every victim circuit, walk the four
   coupling-path families and keep the ones the selection rule asks for
   at that circuit's criticality and exposure. Reject a repeated victim
   identifier and a victim with no criticality on record.
2. Read the declared list and record, for each listed point, the victim
   and the coupling-path family it addresses. A repeated point
   identifier is an input error.
3. Report every derived candidate that the declared list does not
   address as a selection finding.
4. Check each listed point's record: mandatory fields present and not
   blank, coupling path and demonstration method recognized, frequency
   band well formed and rising, required margin finite and not
   negative. Report these rather than raising, so one malformed row
   does not hide the rest of the list.
5. For each point with a required margin, take the demonstrated
   separation as the victim's susceptibility threshold less the
   emission level, and compare it against the requirement. A point with
   a requirement and no demonstrated pair is its own finding.
6. Merge the listed bands into a minimal ascending cover, clip it to
   the project spectrum span and report the uncovered stretches.
7. Take the submission and approval state from the recorded dates. The
   list is compliant only when selection, record, margin and coverage
   findings are all empty and the customer approval is on record with
   an approving party named.

## Pitfalls

- Counting an emission point and a susceptibility point on the same
  conducted path as two points and declaring the family covered twice
  while another family has none. Select against the family.
- Giving every victim a discharge point because discharge is
  fashionable, or giving none because the spacecraft is inside a
  fairing. The rule is exposure-driven for the mission group and
  unconditional only for the safety group.
- Submitting a list whose rows carry a responsible party of "to be
  decided". The point of the deliverable is the commitment, and an
  unassigned row commits nobody.
- Treating a malformed row as fatal and abandoning the review. One bad
  band should be reported alongside the other findings, because the
  customer needs the whole picture in one pass.
- Comparing a demonstrated separation against its requirement with a
  bare greater-or-equal test. The separation is a difference of two
  measured decibel levels and a point exactly on its limit can land a
  few units in the last place below it: subtracting 27.3 from 33.3
  yields 5.9999999999999964, not 6. Absorb the representation error in
  the comparison; never lower the required margin.
- Reading a hair-width hole between two adjoining bands as uncovered
  spectrum. The same 33 MHz edge reached as a tabulated limit and as
  30 MHz carried up by a ten percent overlap differ by about four
  nanohertz, and a bare comparison turns that into a reported gap.
  Judge adjacency with a relative tolerance.
- Recording an approval date with no submission behind it, or dated
  before the submission. Both mean the approval trail is wrong, and
  both are input errors rather than findings to negotiate.
- Treating a list that is out for signature as approved. Awaiting
  approval and approved are different states and the demonstration
  campaign should not start on the first.

## Behavior contract (gate 3)

The coupling-path family, demonstration-method, frequency-band,
selection-rule, candidate-derivation, point-record, demonstrated-
separation, tolerance-absorbing margin, band-merge, coverage-gap,
approval-state and aggregate-review logic is exercised by the gate 3
contract test:
scripts/test_e20_interference_critical_point_list.py against
scripts/e20_interference_critical_point_list_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_interference_critical_point_list.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
