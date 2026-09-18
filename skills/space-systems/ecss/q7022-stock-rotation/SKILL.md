---
name: q7022-stock-rotation
description: "Determine the issue order and lot separation a limited-shelf-life stock holding owes under ECSS-Q-ST-70-22: queue the issuable lots by receipt date with a deterministic tie-break, name where receipt order and expiry order disagree so a later lot expiring sooner is not stranded, raise a finding per bin holding mixed materials, commingled lot numbers without a divider, or quarantined stock beside issuable stock, and grade each actual pick against the queue. Use when stock is binned, a picker questions a lot, or a store is audited. Trigger: ecss, q-st-70-22, shelf-life-stock-rotation, first-in-first-out-issue-order, shelf-life-lot-separation, shelf-life-bin-commingling, out-of-rotation-pick."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-stock-rotation, shelf-life-stock-rotation, first-in-first-out-issue-order, shelf-life-lot-separation, shelf-life-bin-commingling, out-of-rotation-pick]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Stock Rotation and Lot Separation (space-systems/ecss/q7022-stock-rotation)

Use when the task is the stock-control clause of ECSS-Q-ST-70-22: which lot the
store issues next, and whether the way the lots are physically held lets the
wrong one be picked.

## Domain quick reference

- Rotation is an ordering, and an ordering needs a full key. Receipt date alone
  leaves ties, and a tie resolved differently by two people is two different
  queues. Expiry, then lot number, then identity finish the key so the sequence
  is reproducible.
- First-in-first-out and first-expiry-first-out are not the same queue. A lot
  received later can carry the earlier expiry — a short-dated delivery, or a
  lot already part-aged at the supplier — and a receipt-ordered queue strands
  it until it expires on the shelf. The disagreement is worth naming even when
  the declared policy is receipt order.
- Separation is a property of the bin, not of the lot. Two lot numbers of one
  material in one bin are commingled unless a declared divider keeps them
  apart, and two materials in one bin are a finding regardless. The cost is a
  mis-pick that no paperwork afterwards can detect.
- Quarantined stock beside issuable stock is the sharpest version of that
  failure: the lot most likely to be picked by mistake is the one that has
  already been judged unfit.
- A pick is graded against the queue for its own material, not the whole store.
  Passing over two older lots of the same material is the finding; passing over
  an older lot of something else is not.

## Workflow

1. Validate every stock record: identity, material, lot number and bin present,
   receipt and expiry parsable and in order, availability from the known set,
   quantity a non-negative integer. Reject duplicate stock identities.
2. Build the issuable pool: availability issuable and quantity above zero,
   optionally narrowed to one material.
3. Sort the pool under the declared policy with the full tie-break key, and
   report the sequence.
4. Compare the receipt-ordered head with the expiry-ordered head per material
   and raise a rotation conflict naming both lots and their dates.
5. Group the holding by bin and raise separation findings: mixed materials,
   commingled lot numbers with no divider, quarantine not segregated.
6. Grade each actual pick: its position in its material's queue, and every
   older lot passed over. A pick of non-issuable stock fails on its own.
7. Close with the compliance rate and a disposition, with separation findings
   and out-of-rotation picks both fatal and a rotation conflict advisory.

## Pitfalls

- Sorting on receipt date alone. The ties are where two audits of the same
  store produce two different answers.
- Treating a first-expiry conflict as a rule violation. The declared policy
  still governs the pick; the conflict is a stranding risk to be flagged and
  dispositioned, not an automatic non-compliance.
- Grading separation from the stock list rather than the bin map. Lots can be
  perfectly recorded and still be sitting in one open tray.
- Accepting a divider that only one of the commingled lots declares. The
  divider is a property of the arrangement, so every lot sharing the bin has to
  carry it.
- Grading a pick against the whole store's queue. Rotation is per material;
  mixing materials into one sequence invents violations and hides real ones.
- Letting a zero-quantity or already-issued record stay in the queue. It will
  be offered as the next pick and the picker will go to the next real lot,
  quietly out of rotation.

## Behavior contract (gate 3)

The record validation, full-key ordering under both policies, conflict
detection, per-bin separation findings, pick grading against the per-material
queue and the disposition roll-up are exercised by the gate 3 contract test:
scripts/test_q7022_stock_rotation.py against
scripts/q7022_stock_rotation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7022_stock_rotation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
