---
name: q6013-class-2-lot-homogeneity
description: "Determine whether a delivered commercial EEE population may be sampled as one inspection lot at the intermediate assurance class, under ECSS-Q-ST-60-13C clause 5.5.5: place each unit on its wafer lot, assembly lot and site, fall back to a declared equivalence basis where a commercial manufacturer publishes no wafer lot, refuse a unit with neither, compare the date-code span in whole weeks with the limit, count the sub-lots against the cap this class admits, size the sample in exact integer arithmetic and spread it across the sub-lots by largest remainder, then name every sub-lot drawn short of its proportional target. Use when sampling has to be justified as representative. Trigger: ecss, q-st-60-13c-clause-5-5-5, class-two-lot-uniformity, wafer-lot-equivalence-basis, admitted-sub-lot-cap, proportional-sub-lot-allocation, date-code-span-weeks, under-drawn-sub-lot-finding."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-lot-homogeneity, class-two-lot-uniformity, wafer-lot-equivalence-basis, admitted-sub-lot-cap, proportional-sub-lot-allocation, date-code-span-weeks, under-drawn-sub-lot-finding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Lot Homogeneity (space-systems/ecss/q6013-class-2-lot-homogeneity)

Use when the task is the clause 5.5.5 precondition of ECSS-Q-ST-60-13C
at the intermediate assurance class: specimens are about to be drawn for
lot testing, and the result only carries to the delivered parts if the
population behind them can be admitted as one inspection lot.

## Domain quick reference

- The intermediate class does not simply relax the uniformity rule; it
  changes the question. A delivery of several sub-lots may still be
  tested as one inspection lot, and what earns that is a capped number
  of sub-lots plus a sample spread across them in proportion. Sampling
  method is what replaces the single-lot assumption.
- The sub-lot is the tuple of wafer lot, assembly lot and manufacturing
  site — the variables a lot test is meant to hold fixed. Parts sharing
  a marking, a package and a part number can still come from different
  diffusion runs, different assembly runs or different sites.
- Commercial manufacturers frequently publish no wafer lot at all, and
  that is the practical reason this class exists. Where no wafer lot is
  available, a declared equivalence basis may place the unit instead,
  and it has to be declared: a unit with neither closes the assessment,
  because it cannot be placed in any sub-lot and the sample can neither
  reach it nor speak for it.
- Units placed on a basis never share a sub-lot with traced units. The
  basis is a weaker claim, and merging the two would let a traced sub-lot
  absorb parts nobody can trace and report the result as traced.
- The date code is the second axis and it stays independent. A
  population whose codes span many weeks has crossed process
  adjustments the manufacturer never had to declare, so a span limit
  applies even where every sub-lot tuple agrees.
- Proportional allocation has to be reproducible. The sample size and
  the per-sub-lot targets are held in integers and the leftover
  specimens go to the largest remainders with a deterministic tie-break,
  so two sites reviewing the same delivery derive the same targets
  rather than two roundings of the same percentage.
- A sample that meets its total and still leaves a sub-lot under its
  target has said less than the arithmetic suggests. Size and spread are
  different questions, and only the second one is about the parts that
  were not tested.

## Workflow

1. Validate the sampling policy: the sub-lot cap, the date-code span
   limit, the sample ratio as two integers with its floor and cap, the
   allocation slack, and whether an equivalence basis is admitted at
   all. A cap below one, an inverted ratio or a negative slack is
   refused rather than used.
2. Validate every unit: a non-empty identifier, no duplicate identifier,
   an assembly lot, a manufacturing site and a four-digit date code.
   Place a unit carrying a wafer lot on its traced tuple; place one
   without on its declared equivalence basis.
3. Reject a population whose two-digit years straddle a century
   rollover; the span cannot be ordered from the codes alone.
4. Group the units into sub-lots, keeping traced and basis-placed units
   apart, and take the whole-week date-code span of the population.
5. Size the required sample from the lot by exact ceiling division of
   the declared ratio, then apply the floor, the cap and the lot size
   itself as the last bound.
6. Allocate that sample across the sub-lots in proportion to their size
   by the largest-remainder method, capping each target at the sub-lot's
   own size, then map the specimens already drawn onto their sub-lots.
   Refuse a specimen outside the population and one drawn twice.
7. Close on one verdict in precedence order: a unit with no wafer lot
   and no declared basis, a date-code span too wide, more sub-lots than
   the cap admits, a sample undersized or drawn short of a sub-lot's
   target, otherwise a lot the specimens may be drawn from. Report the
   span, the sub-lot count, the required size, the allocation, what was
   drawn in each sub-lot and every finding.

## Pitfalls

- Reading one part number as one inspection lot. The part number is what
  was ordered; the sub-lot tuple is what arrived, and a delivery can
  carry one number and four runs.
- Inventing an equivalence basis at assessment time to place an awkward
  unit. The basis is a declared position taken before the delivery
  arrives; written afterwards, it is a description of the delivery
  chosen to make the delivery pass.
- Folding basis-placed units into a traced sub-lot because everything
  else matches. The traced sub-lot then reports coverage it does not
  have, and the untraceable parts disappear behind a wafer lot that was
  never theirs.
- Treating the date-code span as cosmetic once the sub-lots are inside
  the cap. The two axes are independent: one assembly lot drawn from
  wafers started months apart still spans drift the lot test was
  supposed to bound.
- Computing the per-sub-lot targets as percentages in floating point. A
  sub-lot sitting exactly on the boundary rounds one way on one machine
  and the other on another, and those targets are the numbers two
  reviewers compare.
- Reporting a pass because the total sample size was met. The required
  count can be drawn entirely from the largest sub-lot, which satisfies
  the arithmetic and answers nothing about the rest of the delivery.

## Behavior contract (gate 3)

The policy validation, unit placement including the equivalence basis,
the century-rollover refusal, sub-lot grouping, the date-code span,
integer sample sizing, largest-remainder proportional allocation,
shortfall mapping and the verdict precedence are exercised by the gate 3
contract test:
scripts/test_q6013_class_2_lot_homogeneity.py against
scripts/q6013_class_2_lot_homogeneity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_lot_homogeneity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
