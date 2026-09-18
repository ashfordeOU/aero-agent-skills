---
name: q6005-active-chip-user-lot-testing
description: "Evaluate the sampling and acceptance testing a buyer runs on each delivered batch of active dies. Use when a receiving log has to be dispositioned: size the sample from the lot-size schedule, read the acceptance number it carries, collapse a small batch to full inspection, hold the nonconforming count found against that number, compute the exact hypergeometric probability that a batch carrying a given defect population would still be accepted, confirm every delivery holds its own record, and flag a lot identifier reused across two deliveries. Trigger: ecss, q-st-60-05, user-lot-acceptance-testing, die-delivery-sampling-plan, user-lot-attribute-sample-size, user-lot-acceptance-number, hypergeometric-acceptance-probability, receiving-log-reconciliation, die-lot-identifier-reuse."
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
  tags: [ecss, q-st-60-electronic-components-scope, q6005-active-chip-user-lot-testing, user-lot-acceptance-testing, die-delivery-sampling-plan, user-lot-attribute-sample-size, user-lot-acceptance-number, hypergeometric-acceptance-probability, receiving-log-reconciliation, die-lot-identifier-reuse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Generic Procurement of Active Chips — Active Chip User Lot Testing (space-systems/ecss/q6005-active-chip-user-lot-testing)

Use when the task is the user-lot acceptance testing of ECSS-Q-ST-60-05
clause 8.3.3 -- the buyer's own sampling and testing of each batch of
dies as it is delivered, independent of whatever the supplier recorded
before shipping it.

## Domain quick reference

- The testing belongs to the buyer and it is per delivery. A supplier
  certificate describes the batch as it left the supplier; the user-lot
  test describes it as it arrived, after packing, transit and storage.
- Sample size is not a fixed fraction of the batch. It comes from a
  schedule indexed by lot size, and the acceptance number rises with
  it: a small batch is inspected in full, a mid-size batch tolerates a
  single nonconformity, a large batch a few more.
- A sample larger than the batch is not a plan, it is full inspection.
  Collapsing to the batch size explicitly keeps a small delivery from
  reporting a sample it could not have drawn.
- Inspecting fewer dies than the schedule asks for does not make the
  plan cheaper, it makes the result inadmissible. A short sample cannot
  accept a batch however clean it comes back.
- The plan's real strength is what it would let through. For a given
  defective population in the batch, the probability of acceptance is
  exactly hypergeometric, and it is computed from integer binomials and
  rational arithmetic so the number is identical on every platform
  rather than a float approximation that drifts.
- Reconciliation is part of the clause, not paperwork around it. Each
  delivery owes its own record, and one lot identifier appearing on two
  deliveries means one batch's evidence has been stretched over another
  batch that was never tested.

## Workflow

1. Normalize every receiving-log entry: delivery identifier, lot
   identifier, delivered quantity, and either a nonconforming count
   with the number of dies inspected or an explicit absence of a test.
   Reject a blank identifier, a non-integer quantity and a repeated
   delivery identifier.
2. Size each delivery's sample from the lot-size schedule and read the
   acceptance number that band carries, collapsing to full inspection
   where the sample would exceed the batch.
3. Compare what was actually inspected against the schedule size and
   mark a short sample; a short sample blocks acceptance on its own.
4. Hold the nonconforming count against the acceptance number. A count
   equal to the acceptance number is accepted; one above it is not.
5. Where the plan's strength is in question, compute the exact
   acceptance probability for a hypothesised defective population and
   report it alongside the disposition.
6. Reconcile the log: list every delivery with no user-lot test and
   every lot identifier that appears on more than one delivery.
7. The receiving log conforms only when each delivery was sampled to
   its schedule, each count sat within its acceptance number and no lot
   identifier was reused.

## Pitfalls

- Accepting a delivery on the supplier's own lot data because the
  certificate is in the box -- the clause exists precisely because the
  batch has moved since that data was taken.
- Applying one sample size to every delivery, usually the one that fits
  the budget -- a fixed sample over-tests a small batch and badly
  under-tests a large one.
- Reporting a short sample as a pass because nothing was found in it --
  finding nothing in ten dies where the schedule asked for fifty is not
  evidence about the batch.
- Treating a count equal to the acceptance number as a rejection -- the
  acceptance number is the largest count the plan still accepts, and
  rejecting on it silently tightens the plan.
- Computing the acceptance probability with floating-point powers and
  factorials -- the value then differs between platforms; integer
  binomials with rational arithmetic give one answer everywhere.
- Carrying one lot identifier across two deliveries and testing it once
  -- the second delivery reaches assembly with no evidence at all, and
  the log looks complete.

## Behavior contract (gate 3)

The sampling schedule, full-inspection collapse, short-sample rule,
acceptance-number disposition, exact hypergeometric probability,
receiving-log normalization and reuse reconciliation is exercised by the
gate 3 contract test:
scripts/test_q6005_active_chip_user_lot_testing.py against
scripts/q6005_active_chip_user_lot_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_active_chip_user_lot_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
