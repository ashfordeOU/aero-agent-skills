---
name: q60-class-1-lot-homogeneity-sampling
description: "Use when a sample test result is about to be extended to parts nobody tested. Assess whether the class 1 parts drawn for lot testing genuinely stand for the whole delivered lot under ECSS-Q-ST-60C clause 4.5.5: stratify the lot on its declared production strata, size the required sample by exact integer ratio, allocate that sample across the strata by largest remainder, compare the units actually drawn against the allocation, and weigh the defectives found against the acceptance number. Refuses a part with no stratum label and names every stratum the draw never reached. Trigger: ecss, q-st-60c-clause-4-5-5, class-1-sample-representativeness, lot-stratification-sampling, largest-remainder-allocation, allocation-shortfall-finding, attribute-acceptance-number, unrepresented-stratum-finding."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-lot-homogeneity-sampling, class-1-sample-representativeness, lot-stratification-sampling, largest-remainder-allocation, allocation-shortfall-finding, attribute-acceptance-number, unrepresented-stratum-finding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Lot Homogeneity Sampling (space-systems/ecss/q60-class-1-lot-homogeneity-sampling)

Use when the task is the clause 4.5.5 sampling question of ECSS-Q-ST-60C:
a handful of class 1 parts have been tested, and the result is about to
be written against the whole lot, including the parts nobody touched.
The question is not whether the tested parts passed. It is whether the
parts that were drawn can carry an answer for the ones that were not.

## Domain quick reference

- A lot is rarely a single undifferentiated pile. It arrives in
  production strata — a diffusion block, a build week, a position on the
  panel — and a stratum is exactly the axis along which a part can
  differ from its neighbour. The declared strata are the purchaser's
  statement of where that variation lives, so they are what the draw has
  to span.
- Size and spread are two independent questions. A plan states how many
  units come out of a lot of a given size; nothing in that count says
  where they came from. Drawing the full required count out of one
  stratum satisfies the arithmetic and answers nothing about the rest.
- Proportional allocation is the bridge between the two. A stratum
  holding a fifth of the lot earns a fifth of the sample, and because
  fifths of small samples are not whole units, the leftover units go to
  the largest remainders. Held in integers with a tie broken on the
  stratum label, two reviewers derive the same allocation from the same
  lot.
- A part with no stratum label cannot be placed on the axis at all. It
  is neither a pass nor a fail; it closes the assessment, because a
  representativeness judgement over an unplaceable part is a judgement
  about nothing.
- Acceptance and rejection are not symmetric. An unrepresentative draw
  cannot accept a lot, because acceptance is a claim about the untested
  parts. The same draw can still reject it: finding defectives beyond
  the acceptance number is a claim about parts that were tested, and
  that claim needs no spread argument to stand.
- The sample size follows from the lot size by a declared ratio with a
  floor and a cap. Taken in exact integer arithmetic, a lot sitting
  precisely on the ratio yields the same count everywhere; taken as a
  percentage in floating point, it rounds one way on one machine and the
  other way on another.

## Workflow

1. Validate the lot: every part carries a non-empty identifier and the
   stratum label it was delivered under. A blank label or a duplicate
   identifier is an input error, not a part to be grouped by default.
2. Group the parts into their strata and record the population of each,
   together with the share sitting in the single largest one.
3. Size the required sample from the lot size by exact ceiling division
   of the declared ratio, then apply the floor, the cap, and the lot
   size itself as the last bound.
4. Allocate the required sample across the strata proportionally by the
   largest remainder method, breaking a tie on the stratum label so the
   allocation is reproducible.
5. Map the units actually drawn onto their strata. Refuse a unit that is
   not part of the lot and a unit drawn twice; count what landed where.
6. Take each stratum's shortfall against its allocation and list the
   strata that received nothing at all.
7. Weigh the defectives found against the acceptance number of the plan.
8. Return one verdict in precedence order: defectives beyond the
   acceptance number, a draw short of the required count, a stratum the
   draw never reached, a draw skewed beyond the admitted shortfall,
   otherwise a representative sample whose result carries to the lot.
   Report the strata, the allocation, the shortfalls, the coverage
   fraction and every finding.

## Pitfalls

- Reporting a pass because the required count was drawn. The count is
  arithmetic; representativeness is coverage. Five units out of the
  largest stratum meet the number and leave every other stratum of the
  delivery untested.
- Allocating the sample by rounding a percentage per stratum. The
  rounded parts do not add up to the sample, so somebody quietly adds or
  drops a unit, and which stratum loses it depends on the machine.
  Largest remainder distributes the leftover explicitly.
- Treating a stratum that earned zero units in the allocation as a
  stratum that needs no coverage. A stratum too small to earn a whole
  unit is still material nobody tested; the plan either requires a unit
  from it or admits the gap in writing.
- Letting a part with a blank stratum ride along because the rest of the
  lot is labelled. The draw either misses that part or misrepresents it,
  and neither outcome is visible in the numbers afterwards.
- Withholding a rejection because the draw was not representative.
  Defectives found are evidence about tested parts; the asymmetry
  between accepting and rejecting is deliberate and has to survive into
  the verdict.
- Widening the admitted shortfall until a skewed draw passes. The
  shortfall tolerance describes what the plan accepts before the draw,
  not a dial turned afterwards to make one delivery come out clean.

## Behavior contract (gate 3)

The part validation, stratification, integer sample sizing, largest
remainder allocation, draw mapping, shortfall and coverage measures,
acceptance-number evaluation and verdict precedence are exercised by the
gate 3 contract test:
scripts/test_q60_class_1_lot_homogeneity_sampling.py against
scripts/q60_class_1_lot_homogeneity_sampling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_lot_homogeneity_sampling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
