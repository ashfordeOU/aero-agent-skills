---
name: q6012-wafer-level-deliverables
description: "Determine the deliverable set an accepted wafer batch owes and reconcile it against what the foundry actually handed over, per ECSS-Q-ST-60-12C clause 10.2.6: derive the required items from the batch conditions, validate the supplied list, and separate satisfied from missing, unusable and surplus. Treats a draft, an unsigned copy, a superseded issue and a right document at the wrong revision as four distinct unusable states, each with its own reason. Use when a wafer batch arrives and its paperwork decides whether it is taken. Trigger: ecss, q-st-60-12c-clause-10-2-6, wafer-batch-deliverable-set, foundry-handover-documentation, wafer-batch-revision-mismatch, accepted-die-wafer-map, wafer-batch-completeness-fraction."
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
  tags: [ecss, q-st-60-12-wafer-level-deliverables, q6012-wafer-level-deliverables, wafer-batch-deliverable-set, foundry-handover-documentation, wafer-batch-revision-mismatch, accepted-die-wafer-map, wafer-batch-completeness-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wafer-Level Deliverables (space-systems/ecss/q6012-wafer-level-deliverables)

Use when an accepted wafer batch is being handed over and the question is
whether everything that has to travel with it actually did — the data, the
identification, the map and the instructions that make the batch usable to
the buyer rather than just present in the buyer's stores.

## Domain quick reference

- The deliverable set is derived, not fixed. A batch handed over as separated
  die owes the map that locates the accepted dies and the handling
  instruction the package no longer provides; the same batch kept at wafer
  level owes neither. A first lot, a process change, a radiation environment
  and a raised deviation each add their own item.
- Measurement data with no limits behind it is unusable. The acceptance
  numbers only mean something against the foundry's own parameter limits, so
  both travel together and both are graded as required items.
- A document exists in more states than present and absent. Draft, unsigned,
  superseded and issued-at-the-wrong-revision are four different failures with
  four different fixes, and collapsing them into one missing count sends the
  foundry looking for a document that is already on the desk.
- Revision is part of identity. A correctly titled, properly issued, signed
  document written against the previous batch revision is evidence about a
  different batch, and it is the failure most easily read as a pass.
- A surplus item is a question, not a fault. Something supplied that this
  batch does not owe usually means paperwork from a neighbouring batch has
  been included, so it is reported without withholding the delivery.

## Workflow

1. Validate the batch case: batch identity, the revision the paperwork has to
   match, and the condition flags, refusing an unknown key so a misspelt flag
   cannot drop a whole item out of the required set.
2. Derive the required deliverables from those conditions, keeping the reason
   each item was required so the list can be defended to the foundry.
3. Validate what was supplied: known items, known statuses, nothing supplied
   twice, and no unrecognised field smuggled into a record.
4. Reconcile the two sets. An item is satisfied only when it is issued and at
   the batch revision; every other state is unusable and is reported with the
   specific reason.
5. Report missing, unusable and surplus separately, with the completeness
   fraction over the required set rather than over what arrived.
6. Withhold the batch when anything required is missing or unusable; accept it
   when only surplus remains, with the surplus flagged.

## Pitfalls

- Grading the handover against a standard checklist. The batch that stayed at
  wafer level does not owe a die handling instruction, and marking it short
  produces an argument the buyer loses.
- Counting completeness over what arrived. Ten documents out of ten supplied
  is a full delivery of the wrong set; the denominator is what was owed.
- Accepting a properly issued document at the previous revision. It is the
  most convincing wrong answer in the pile, because everything about it looks
  right except the batch it describes.
- Treating a draft as a document. A draft has no owner and can change after
  the batch is built into hardware; it is not evidence of anything yet.
- Withholding a batch over a surplus item. The extra document is a
  housekeeping question; treating it as a shortfall delays delivery for a
  reason the foundry cannot act on.

## Behavior contract (gate 3)

The case validation, condition-driven derivation of the required set, supplied
list validation, the four unusable states including the revision mismatch, the
completeness fraction over the required set and the accept-or-withhold
decision are exercised by the gate 3 contract test:
scripts/test_q6012_wafer_level_deliverables.py against
scripts/q6012_wafer_level_deliverables_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_wafer_level_deliverables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
