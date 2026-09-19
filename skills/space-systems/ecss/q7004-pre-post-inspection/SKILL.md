---
name: q7004-pre-post-inspection
description: "Evaluate a thermally tested item against its before-and-after inspection records for damage, distortion and degradation. Use when the ECSS-Q-ST-70-04C evaluation clauses require the test's effect to be separated from what the item arrived with: compare each recorded dimension against its distortion tolerance, difference the two defect registers into new, grown and unaccounted entries, reduce the mass records to a signed change fraction, reduce each performance pair to a degradation fraction, then group the anomalies into a disposition of accept, review or reject. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-pre-post-inspection, post-thermal-distortion-check, thermal-defect-register-difference, post-thermal-mass-loss, thermal-degradation-disposition."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-pre-post-inspection, thermal-pre-post-inspection, post-thermal-distortion-check, thermal-defect-register-difference, post-thermal-mass-loss, thermal-degradation-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Pre-Test and Post-Test Inspection (space-systems/ecss/q7004-pre-post-inspection)

Use when the task is the inspection side of the ECSS-Q-ST-70-04C evaluation
clauses — reading the record taken before the item went into the chamber
against the record taken when it came out, and saying what the test did to it.

## Domain quick reference

- The pre-test inspection is the only thing that makes the post-test one
  informative. Without it, every mark on the hardware is arguable; with it,
  the difference between the two registers is the test's effect and nothing
  else.
- Three effects are looked for and they fail differently. Distortion is
  dimensional and is compared against a per-dimension tolerance; damage is a
  defect register difference; degradation is a change in a measured property,
  mass or performance, that leaves the item intact but worse.
- A defect register is differenced by identifier, not by count. What matters
  is which entries are new, which grew beyond the growth tolerance, and which
  the post-test register fails to account for at all.
- A pre-test defect that has vanished from the post-test register is a
  records problem, not good news. Either the inspection missed it or the two
  registers describe different hardware, and both need closing before the
  item is dispositioned.
- Severity decides the disposition, not the number of anomalies. A single new
  crack or delamination is unusable hardware; a patch of coating loss is
  something a review board judges against the application.
- Mass loss and mass gain are not symmetric. Loss is outgassing or material
  leaving, which is what the allowance exists for; a gain is contamination and
  is never netted against a loss to make a smaller number.
- A dimension recorded only once is not a pass. Nothing was compared, so the
  result is an open item rather than a clean one.

## Workflow

1. Compare every dimension the tolerance table names, computing the
   distortion as the magnitude of the change and flagging any dimension that
   only one of the two records carries.
2. Validate and index both defect registers by identifier, refusing a
   register that lists the same identifier twice.
3. Difference the registers into new, grown, unchanged and unaccounted
   entries, using the declared growth tolerance to decide what counts as
   growth.
4. Group the new and grown entries by kind so the critical ones are separated
   from the ones a review board can weigh.
5. Reduce the mass records to a signed change fraction, take the loss as the
   negative part only, and compare it with the allowance.
6. Reduce each performance pair to a degradation fraction and compare it with
   its own allowance.
7. Sort every anomaly into blocking or reviewable and return the disposition
   they imply, with all findings.

## Pitfalls

- Reading the post-test inspection on its own. Half the marks on a used piece
  of hardware predate the test, and without the pre-test register there is no
  way to say which half.
- Counting defects instead of differencing them. Two registers with the same
  number of entries can describe completely different damage.
- Netting a mass gain against a mass loss. Contamination and material loss
  are different mechanisms and the sum of the two hides both.
- Treating a vanished pre-test defect as a repair. It is an unclosed
  discrepancy between two records, and it stays open until someone explains
  it.
- Letting a long list of cosmetic findings outweigh a single structural one.
  The disposition turns on the worst anomaly, not on how many there are.
- Comparing a distortion, a mass loss or a degradation against its allowance
  with a bare strict inequality. All three are floats built from
  subtractions and divisions, so a value sitting on the allowance is compared
  within a named tolerance while the allowance stays as specified.

## Behavior contract (gate 3)

The dimension comparison, defect-register validation and differencing with
the critical grouping, mass change fraction, performance degradation and the
combined accept/review/reject disposition are exercised by the gate 3
contract test: scripts/test_q7004_pre_post_inspection.py against
scripts/q7004_pre_post_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_pre_post_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
