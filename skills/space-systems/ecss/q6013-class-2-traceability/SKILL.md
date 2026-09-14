---
name: q6013-class-2-traceability
description: "Verify that a commercial EEE lot keeps a traceability record across every handling step it passes through at the intermediate assurance class, under ECSS-Q-ST-60-13C clause 5.5.4: bridge a re-lotted record only on a cross-reference back to the lot under investigation, discount a record held by another party until an access undertaking is recorded, report plain and credited step coverage against separate floors, name each record kept for fewer years than the retention floor, and catch a record dated against the order its handling step occurs in. Use when a lot's handling records have to become a coverage verdict rather than a folder. Trigger: ecss, q-st-60-13c-clause-5-5-4, class-two-commercial-eee-lot-traceability, handling-step-record-coverage, externally-held-traceability-record, traceability-record-retention-floor, lot-cross-reference-bridge, handling-step-record-order."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-traceability, class-two-commercial-eee-lot-traceability, handling-step-record-coverage, externally-held-traceability-record, traceability-record-retention-floor, lot-cross-reference-bridge, handling-step-record-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Lot Traceability (space-systems/ecss/q6013-class-2-traceability)

Use when the task is the clause 5.5.4 traceability duty of
ECSS-Q-ST-60-13C at the intermediate assurance class: one commercial lot
has moved from goods-in to a delivered assembly, and the question is
whether a record exists at every handling step it passed through, who is
holding each one, and whether they still describe the same lot.

## Domain quick reference

- Traceability at this class is graded by step, not by part. The record
  that matters is the one covering receipt, incoming inspection,
  storage, kitting, assembly and delivery; a step with nothing on file
  is where the lot stops being followable, and no amount of detail in
  the neighbouring steps recovers it.
- The steps have one possible order, and the dates have to agree with
  it. A kitting record dated before the receipt it drew from means the
  clock, the identity or the record itself is wrong, and all three
  invalidate the same thing: the claim that these records describe one
  journey.
- Re-lotting is legitimate here and it is bridged, not waved through. A
  record naming a different lot stays on the chain only against a
  cross-reference back to the lot under investigation, and that bridge
  is reported rather than absorbed, because a reviewer who cannot see it
  cannot check it.
- The intermediate class admits a record held by somebody else — a
  distributor, a subcontractor, an assembly house — which the class
  above does not. What makes it admissible is a recorded access
  undertaking: a record the project cannot reach when the alert arrives
  is a record it does not have.
- Two coverage figures travel together. The plain figure says how many
  steps carry a record at all; the credited figure weighs an externally
  held record below one held here, so a lot traced entirely through
  other people's filing systems reads differently from one traced in
  house, and the difference shows before it is tested.
- Retention is part of the record, not an archiving detail. A commercial
  part outlives the contract that bought it, and a record scheduled for
  destruction before the mission ends is a traceability gap with a date
  on it rather than a gap already open.

## Workflow

1. Validate the traceability policy: the required handling steps, the
   plain and credited coverage floors, the credit an externally held
   record earns, the retention floor in whole years and the two
   permissions — access undertakings and cross-reference bridging. A
   step list with no receipt, or a credited floor above the plain floor,
   is refused rather than used.
2. Validate every record: a non-blank identifier, no duplicate
   identifier, a recognised handling step, a lot code, a known holder, a
   non-negative retention period and an integer day. A record held here
   that carries an access undertaking is an input error.
3. Resolve identity against the lot under investigation. A record
   naming that lot is on the chain; a record naming another lot joins it
   only on a cross-reference back, and is an identity break otherwise.
4. Dispose each required step: held here, held by another party under a
   recorded undertaking, held outside with no undertaking, or missing.
   Where a step has both kinds of record, the one held here governs.
5. Take the plain coverage over the required steps and the credited
   coverage with the external credit applied, name every uncovered step,
   and compare both figures with their floors through a tolerance so a
   coverage landing exactly on a floor reads as met.
6. Name every record kept for fewer whole years than the floor, then
   walk the surviving records in step order and report each one dated
   before a record from an earlier step.
7. Close on one verdict in precedence order: chain not established, lot
   identity broken, access undertaking missing, step coverage short,
   retention below the floor, records out of order, or traceability that
   meets the intermediate class. Report both coverages, each step's
   disposition, the bridges taken and every finding.

## Pitfalls

- Reading a thick folder as coverage. The question is which steps carry
  a record, and a lot with four records at receipt and none at kitting
  scores worse than one with a single record per step, however much
  paper the first one weighs.
- Accepting a supplier's record because the supplier is reliable. The
  undertaking is what makes the record reachable in the year the alert
  lands, and reliability is not a mechanism for getting a file back from
  a company that has since been sold.
- Absorbing a cross-reference into the chain silently. The bridge is the
  one place a second lot could have entered the record, so it is
  reported beside the verdict rather than resolved out of sight.
- Averaging the plain coverage alone. A lot whose every record sits with
  other parties reaches full plain coverage and is a materially weaker
  position than one traced in house, which is exactly what the credited
  figure exists to show.
- Ordering the records by the row order of the extract. Records arrive
  in whatever order the system exported them; the handling step gives
  the order and the day has to agree with it, and a tie needs a
  deterministic second key or two runs disagree.
- Treating retention as somebody else's problem. A record with two years
  left on a ten-year mission is a gap with a date on it, and it is far
  cheaper to extend the retention now than to reconstruct the lot later.

## Behavior contract (gate 3)

The policy validation, record validation, identity resolution and
cross-reference bridging, the step disposition including externally held
records, the plain and credited coverages against their floors, the
retention floor, the step-order reading and the verdict precedence are
exercised by the gate 3 contract test:
scripts/test_q6013_class_2_traceability.py against
scripts/q6013_class_2_traceability_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_2_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
