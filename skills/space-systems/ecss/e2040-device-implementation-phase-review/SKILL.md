---
name: e2040-device-implementation-phase-review
description: "Determine whether the device implementation phase review may release validation, qualification and acceptance work. Use when an ECSS-E-ST-20-40C clause 5.7.5 gate is being held: resolve which phase outputs the device criticality category actually owes, assess each one for presence, maturity and customer approval, weigh the open review actions and nonconformances by severity, escalate an overdue minor action to a blocking one, and return proceed, proceed-with-actions or hold with every finding behind it. Refuses an unknown category, an unrecognised output name, an open action naming no owner and a duplicate identifier. Trigger: ecss, e-st-20-40c, device-implementation-phase-review, device-criticality-applicability, phase-output-maturity, overdue-review-action-escalation, open-nonconformance-disposition, phase-gate-disposition."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-implementation-phase-review, device-criticality-applicability, phase-output-maturity, overdue-review-action-escalation, open-nonconformance-disposition, phase-gate-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Implementation Phase Review (space-systems/ecss/e2040-device-implementation-phase-review)

Use when the task is the implementation phase review of ECSS-E-ST-20-40C
clause 5.7.5 — the customer-led gate that closes the implementation phase of
an ASIC, FPGA or IP core and decides whether validation, qualification and
acceptance work may proceed, be started under carried actions, or be held.

## Domain quick reference

- The owed output set is not fixed. It is derived from the device
  criticality category and the procurement route, so a lighter-category
  device carries the build evidence without the formal part-evaluation
  paperwork. Demanding the full set of every device produces findings a
  reviewer will strike out, and accepting the light set for a high
  category lets a real gap through.
- An output can be present and still not satisfy the gate. Presence,
  maturity and customer approval are three separate states, and a
  submitted-but-draft item is a different finding from an absent one.
  Maturity above what the gate needs is fine; it is not an anomaly.
- An output submitted that the category does not owe is worth reporting
  without holding the gate. It usually means the applicability tailoring
  and the delivery list disagree, which is cheap to settle now and
  expensive to discover during acceptance.
- Open review actions are not equal. A major or critical one holds the
  gate outright, and an overdue minor one does too — an action already
  past its date will not be worked in the window before validation
  starts, so its original severity has stopped being informative.
- Nonconformances are read on their disposition, not their existence. An
  accepted, repaired or scrapped item is closed for this gate; only one
  still open counts, and only a major or critical open one holds.

## Workflow

1. Normalise the criticality category and derive the owed output set
   from it. An unknown category is an input error, not a default to the
   heaviest set.
2. Validate each submitted output: a name outside the phase output list,
   an unknown maturity word, a non-boolean approval flag or a duplicate
   submission is refused rather than scored.
3. Partition the owed set into absent, present-but-immature and
   present-but-unapproved, and separately collect outputs submitted that
   the category does not owe.
4. Validate the review actions. An open action with no owner is refused;
   a non-integer date offset is refused.
5. Compute the open-action load with severity weights, escalating any
   overdue open action to at least the blocking weight, and collect the
   blocking identifiers.
6. Collect the open nonconformances and the blocking subset of them.
7. Return hold if any owed output is absent, immature or unapproved or
   any blocking action or nonconformance is open; proceed-with-actions
   if only non-blocking items remain open; proceed otherwise. Report
   every finding that produced the disposition.

## Pitfalls

- Applying the category A output list to every device. The applicability
  table is the first step of this gate, not a formality, and using the
  wrong one inverts the result in both directions.
- Collapsing presence, maturity and approval into one pass or fail. The
  three drive different recovery actions, and a reviewer needs to know
  which of them a held gate turned on.
- Letting an overdue minor action ride as a carried action. The date has
  already passed; carrying it into validation is how a minor item
  becomes an acceptance-stage surprise.
- Holding the gate on an open minor nonconformance. That over-restricts
  the disposition and trains teams to hide items rather than record
  them; the minor open item belongs in the carried-action list.
- Counting a nonconformance that has already been dispositioned. Open is
  a disposition state, not the absence of one, and accepted or repaired
  items are done for this gate.
- Reading a proceed-with-actions disposition as a clean gate. It is a
  release with an outstanding list, and the list has to be visible in
  the report for the disposition to mean anything.

## Behavior contract (gate 3)

Category normalisation, applicability resolution, output presence, maturity
and approval assessment, action severity weighting with overdue escalation,
nonconformance disposition handling and the three-way gate decision are
exercised by the gate 3 contract test:
scripts/test_e2040_device_implementation_phase_review.py against
scripts/e2040_device_implementation_phase_review_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_implementation_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
