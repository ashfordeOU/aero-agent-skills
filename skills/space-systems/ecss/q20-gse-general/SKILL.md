---
name: q20-gse-general
description: "Audit the general quality assurance requirements that follow ground support equipment under ECSS-Q-ST-20C clause 5.8.8: test each identification mark against the marking scheme, catch a mark repeated across the register and a mark on the item that disagrees with the register entry, derive the record set the item's category and states demand, size the record retention shortfall in years against service life plus margin, and name every handling provision a safety-critical item owes at its point of use. Use when a GSE register or a single item's file is being reviewed. Trigger: ecss, q-st-20c-clause-5-8-8, gse-identification-marking, gse-register-duplicate-mark, gse-record-retention-shortfall, gse-safety-critical-handling-provision, gse-file-completeness."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-general, gse-identification-marking, gse-register-duplicate-mark, gse-record-retention-shortfall, gse-safety-critical-handling-provision, gse-file-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS General GSE Quality Assurance (space-systems/ecss/q20-gse-general)

Use when the task is the clause 5.8.8 general quality assurance requirements
for ground support equipment in ECSS-Q-ST-20C: the equipment has to be
identifiable on sight, the records that follow it have to survive it, and
equipment whose failure would hurt someone has to carry the provisions its
category demands.

## Domain quick reference

- Identification is a property of the item, not of the spreadsheet. A mark
  follows a scheme, is applied durably enough to outlive the paint, and reads
  the same on the hardware as in the register.
- A mark repeated on two items identifies neither. The duplicate is not a
  tidiness problem; it is the reason a usage log gets appended to the wrong
  trolley for two years.
- The record set is derived from the item. Everything owes the base file;
  something categorized safety-critical owes its inspection record and its
  operator training record; a calibrated chain owes its calibration history; a
  software-driven unit owes its configuration record.
- Retention is measured against the item's life, not against a filing policy.
  Records that expire while the equipment is still lifting cannot answer the
  question the next investigation will ask, and the shortfall is reported in
  years so it can be closed.
- Safety-critical provisions live at the point of use. A procedure in a server
  and a hazard notice nobody hung are the same amount of protection.
- Fitness for registered use is the conjunction of all three: identification,
  records and provisions. Two out of three is an item nobody can account for.

## Workflow

1. Validate each register entry: a mark, a category from the closed vocabulary,
   the mark actually carried on the item, and durability stated rather than
   assumed.
2. Test every mark against the marking scheme and raise a malformed one.
3. Detect a mark carried by more than one item across the whole register, not
   just within a page of it.
4. Compare the mark on the item with the mark in the register and raise the
   unmarked and the mismatched cases separately.
5. Derive the mandatory record set from the item's category and states, then
   name each record the file does not hold.
6. Compute the retention shortfall against service life plus margin, returning
   zero when retention exactly meets the requirement.
7. For a safety-critical item, name each absent handling provision on its own,
   then combine every finding into the fitness decision.

## Pitfalls

- Auditing the register instead of the hardware. The entry is a claim about a
  mark; the item is where the mark either is or is not.
- Accepting a hand-written label as identification. A mark that the next wash
  removes takes the equipment's whole history with it.
- Reading a unique-looking mark as unique. Duplicates appear when two sites
  number their own fleets, and only a register-wide check finds them.
- Applying one record set to every item. A calibrated, software-driven
  safety-critical rig owes four records that a plain stand does not.
- Reporting retention as compliant or not. The useful answer is the number of
  years the file is short by, because that is what the fix has to buy.
- Treating a written procedure as a provision in place. The provision is at the
  point of use — the notice on the equipment, the restriction on who may touch
  it, the interval at which it is looked at.

## Behavior contract (gate 3)

The register entry validation, marking-scheme test, register-wide duplicate
detection, item-versus-register mark reconciliation, the category-derived
record set, the retention shortfall in years, the safety-critical handling
provisions and the combined fitness decision are exercised by the gate 3
contract test: scripts/test_q20_gse_general.py against
scripts/q20_gse_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_gse_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
