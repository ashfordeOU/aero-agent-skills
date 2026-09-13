---
name: e2006-internal-grounding-inspection
description: "Use when audit a structure-and-harness grounding inspection campaign under ECSS-E-ST-20-06C clause 9.3 and prove that no internal metallic item was left ungrounded: build the inventory of internal-metallic-items from the structure and harness build records, match each item to an inspection record, check the record used a method valid for that item family -- visual-bond-inspection, bond-resistance-measurement or shield-continuity-check -- read the measured bond-resistance against the item limit, and report uncovered items, inconclusive records, orphan records and ungrounded findings alongside an inspection-coverage ratio. Trigger: ecss, e-st-20-electrical-scope, grounding-inspection, internal-metallic-item, bond-resistance-measurement, shield-continuity-check, inspection-coverage-gap, inconclusive-inspection-record, internal-electrostatic-discharge."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-internal-grounding-inspection, grounding-inspection, internal-metallic-item, bond-resistance-measurement, shield-continuity-check, inspection-coverage-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design -- Internal Grounding Inspection (space-systems/ecss/e2006-internal-grounding-inspection)

Use when the task is the clause 9.3 verification of ECSS-E-ST-20-06C:
the structure and the harness are inspected item by item, and the
campaign closes only when every internal metallic item on the inventory
has an inspection record that actually establishes it is grounded.

## Domain quick reference

- The clause is a coverage obligation before it is a measurement
  obligation. The failure it guards against is an item nobody looked
  at -- a bracket added late, a shield terminated at one end only, a
  screened housing that arrived with its bond strap in the bag. An
  item that never entered the inventory cannot be reported as
  grounded, so the inventory is built from the structure and harness
  build records rather than from the inspection sheets.
- Each inspection record has a method, and not every method settles
  every item family. A visual-bond-inspection confirms a strap is
  fitted and torqued; it does not confirm the path conducts, so on a
  shield or an enclosure it is inconclusive on its own and has to be
  backed by a measurement. A bond-resistance-measurement settles any
  family. A shield-continuity-check settles a shield and applies to
  nothing else.
- A record that reports a measurement carries a measured resistance in
  ohm, and that number is read against the bond limit for the item
  family -- tighter for shield and enclosure terminations than for a
  bolted structural bond. Over the limit is an ungrounded finding, not
  a note.
- An inspection record that names an item absent from the inventory is
  an orphan. It is a finding in its own direction: either the
  inventory is incomplete or the record refers to hardware that is not
  on this build, and both cases need closing before the campaign is
  signed.
- The campaign verdict is the coverage ratio plus the finding lists.
  A coverage ratio of one with an inconclusive record on it is still
  an open campaign.

## Workflow

1. Build the inventory from the structure and harness build records.
   Categorize each item into its bonding family; reject an
   unrecognized item kind and a duplicate item identifier rather than
   silently collapsing them.
2. Normalize each inspection record: item reference, method,
   inspector, and -- for a measuring method -- a finite non-negative
   measured resistance. Reject a record with a method not on the
   recognized list.
3. Match records to inventory items. Items with no record are coverage
   gaps; records naming no inventory item are orphans.
4. For each matched pair, check the method is applicable to the item
   family. A method outside the family's applicable set makes the
   record inapplicable, which leaves the item uncovered in substance
   even though a sheet exists.
5. Evaluate each applicable record: a non-measuring method on a family
   that needs a number is inconclusive; a measured resistance at or
   below the family bond limit is grounded; above it is ungrounded.
   Absorb the representation error of the comparison at the limit
   rather than widening the limit.
6. Aggregate: coverage ratio, ungrounded items, inconclusive items,
   inapplicable records, orphan records. The campaign closes only when
   coverage is complete and every finding list is empty.

## Pitfalls

- Building the inventory from the inspection sheets. That makes the
  coverage ratio one by construction and hides exactly the item the
  clause exists to catch -- the one nobody inspected.
- Accepting a visual-bond-inspection as closure on a shield or a
  screened housing. It confirms the hardware is fitted, not that the
  path conducts; treating it as a pass turns an inconclusive record
  into a false green.
- Applying a shield-continuity-check to a bracket or a baseplate. The
  method does not address a bolted structural bond, and a record
  outside its applicable family is inapplicable rather than a pass.
- Discarding orphan records as clerical noise. An orphan says the
  inventory and the build disagree, which is a finding about the
  inventory, not about the record.
- Reading a coverage ratio of one as a closed campaign while an
  inconclusive or ungrounded finding is still open -- coverage is
  necessary, never sufficient.
- Treating a measurement that lands a few units in the last place over
  the family bond limit as an ungrounded finding; the comparison
  absorbs the float representation error while the limit itself stays
  exactly where the design set it.

## Behavior contract (gate 3)

The inventory categorization, record normalization, method
applicability, per-record evaluation, coverage matching and campaign
roll-up logic is exercised by the gate 3 contract test:
scripts/test_e2006_internal_grounding_inspection.py against
scripts/e2006_internal_grounding_inspection_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2006_internal_grounding_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
