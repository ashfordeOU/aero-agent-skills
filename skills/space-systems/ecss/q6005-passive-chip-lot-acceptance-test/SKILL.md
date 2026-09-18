---
name: q6005-passive-chip-lot-acceptance-test
description: "Evaluate the lot acceptance evidence behind an incoming batch of passive chips for hybrid assembly under ECSS-Q-ST-60-05C clause 8.2.3. Use when the task is sizing the attribute sample a lot owes from its population, setting the acceptance number a destructive test drives to zero, computing the observed defective fraction and the lot tolerance the plan actually buys, grading that fraction against the percent-defective-allowable its chip family carries, and refusing a rejected lot resubmitted without an approved rescreen. Trigger: ecss, q-st-60-05c, hybrid-passive-chip-lot-acceptance, passive-chip-sampling-plan, passive-chip-acceptance-number, passive-chip-defective-fraction, passive-chip-lot-tolerance, passive-chip-rescreen-resubmission."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-passive-chip-lot-acceptance-test, hybrid-passive-chip-lot-acceptance, passive-chip-sampling-plan, passive-chip-acceptance-number, passive-chip-defective-fraction, passive-chip-lot-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Passive Chip Lot Acceptance Test (space-systems/ecss/q6005-passive-chip-lot-acceptance-test)

Use when the task is the incoming lot acceptance of ECSS-Q-ST-60-05C
clause 8.2.3 — deciding how large a sample a delivered batch of passive
chips owes, how many defectives that sample may carry, and whether the
result the sample returned accepts the lot or sends it back.

## Domain quick reference

- Acceptance is made on a sample, so the sample size is the first
  decision and it comes from the lot population, not from convenience.
  The plan moves in bands: a lot of forty and a lot of four hundred do
  not owe the same number of pieces. A sample drawn smaller than the
  band requires is not a cheaper version of the plan, it is a different
  plan with a worse tolerance, and a sample larger than the lot it came
  from is an input error.
- The acceptance number depends on what the test does to the piece. A
  non-destructive test returns its sample to the lot, so it can tolerate
  a small number of defectives, and the number it tolerates grows with
  the sample. A destructive test consumes everything it touches, so the
  evidence is bought with the parts themselves and the acceptance number
  is zero: one defective is one failed lot.
- Two criteria decide a lot and they are not the same criterion. The
  count is graded against the acceptance number; the observed defective
  fraction is graded against the percent-defective-allowable the chip
  family carries. A mid-size sample can sit inside its acceptance number
  while its fraction is well over the allowable for a dielectric part,
  and that lot fails on the fraction.
- A plan that accepts on zero defectives still passes lots with a real
  defect rate, and the lot tolerance percent defective states how large
  that rate can be at ninety percent confidence. It is the honest
  description of what the sampling bought and it is reported alongside
  the disposition, not left implied.
- A lot rejected once is not made acceptable by being offered again. It
  is admissible only after a rescreen, and only when that rescreen has
  an approval on record; otherwise the second presentation carries the
  first result with a new delivery date on it.

## Workflow

1. Validate each lot record: identifier, chip family, test kind, lot
   size, sample drawn and defectives found. An unknown family, an
   unknown test kind, a non-positive lot size or more defectives than
   the sample held are input errors, not degenerate cases to clamp.
2. Size the sample the lot owes from its population band, and cap it at
   the lot itself so a tiny lot is not asked for more pieces than it
   contains.
3. Read the acceptance number: zero for a destructive test kind, and the
   banded value for a non-destructive one.
4. Compute the observed defective fraction, and the lot tolerance the
   sample size and acceptance number together buy at ninety percent
   confidence.
5. Grade the count against the acceptance number and the fraction
   against the family allowable, absorbing the quotient representation
   error at the boundary with a named tolerance rather than by widening
   the allowable.
6. Check the sampling itself and the resubmission history: an undersized
   sample, a sample exceeding the lot, a destructive test that would
   consume the whole lot, an unrescreened resubmission and an
   unapproved rescreen are each their own finding.
7. Aggregate the delivery: report accepted and rejected lots separately,
   the pieces sampled, the pieces consumed destructively, and the worst
   lot tolerance any lot in the delivery carries.

## Pitfalls

- Drawing a convenient sample and keeping the plan's acceptance number.
  The two are one object; a smaller sample changes what the acceptance
  number means and silently loosens the tolerance behind it.
- Giving a destructive test a non-zero acceptance number because the
  sample was large. Size does not restore the pieces the test consumed,
  and a second defective cannot be confirmed against a lot that no
  longer contains the parts it came from.
- Grading only the count. A lot inside its acceptance number can still
  be over the fraction its chip family allows, and a family whose
  failure mode shorts a dielectric is held tighter than one that drifts.
- Reporting a disposition without the lot tolerance. Accepted on zero
  out of eight and accepted on zero out of two hundred read the same in
  a summary and are two very different statements about the population.
- Accepting a resubmitted lot on its new paperwork. Without a rescreen
  and an approval on record, the lot presented the second time is the
  lot that was rejected the first time.

## Behavior contract (gate 3)

The sample sizing, acceptance-number selection, defective-fraction and
lot-tolerance computation, family-allowable grading, resubmission checks
and delivery aggregation are exercised by the gate 3 contract test:
scripts/test_q6005_passive_chip_lot_acceptance_test.py against
scripts/q6005_passive_chip_lot_acceptance_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_passive_chip_lot_acceptance_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
