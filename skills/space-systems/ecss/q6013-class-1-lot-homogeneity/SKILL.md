---
name: q6013-class-1-lot-homogeneity
description: "Assess whether a delivered class 1 component population is one genuinely uniform production lot before test specimens are drawn from it under ECSS-Q-ST-60-13C clause 4.5.5: group the units by wafer lot, assembly lot and manufacturing site, count the traceability groups, compare the date-code span in whole weeks with the declared limit, size the sample from the lot in exact integer arithmetic, and confirm the drawn specimens reach every sub-lot instead of clustering in the largest one. Refuses a unit carrying no traceability and names each sub-lot the sample never touched. Use when sampling has to be justified as representative of the whole lot. Trigger: ecss, q-st-60-13c-clause-4-5-5, class-1-lot-homogeneity, wafer-lot-traceability-grouping, date-code-span-weeks, lot-sample-size-derivation, sub-lot-sampling-coverage, unsampled-sub-lot-finding."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-lot-homogeneity, class-1-lot-homogeneity, wafer-lot-traceability-grouping, date-code-span-weeks, lot-sample-size-derivation, sub-lot-sampling-coverage, unsampled-sub-lot-finding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 Lot Homogeneity (space-systems/ecss/q6013-class-1-lot-homogeneity)

Use when the task is the clause 4.5.5 precondition of ECSS-Q-ST-60-13C:
specimens are about to be drawn for class 1 lot testing, and the result
only carries to the delivered parts if the population they came from is
one uniform production lot rather than a delivery assembled from
whatever the distributor had on the shelf.

## Domain quick reference

- Uniformity is a traceability statement, not a visual one. Parts that
  share a marking, a package and a part number can still come from
  different diffusion runs, different assembly runs or different sites,
  and those are the variables a lot test is meant to hold fixed. The
  sub-lot is therefore the tuple of wafer lot, assembly lot and site,
  and the count of distinct tuples is the count of real lots in the box.
- The date code is the second axis. A population whose codes span many
  weeks has crossed process adjustments the manufacturer never had to
  declare, so a span limit applies even when every traceability tuple
  agrees. Two axes, two independent ways one delivery stops being one
  lot.
- A unit with no traceability data cannot be placed on either axis. It
  is not a unit that passes by default and it is not a unit that fails;
  it closes the assessment, because a homogeneity judgement over an
  unplaceable unit is a judgement about nothing.
- Sample size follows from lot size by a declared ratio with a floor and
  a cap. Held in integers, the same lot size yields the same count
  everywhere; held in floating point, a lot sitting exactly on the ratio
  rounds one way on one machine and the other way on another.
- A sample that never reaches a sub-lot has said nothing about it.
  Where a delivery of several sub-lots is admitted at all, coverage of
  each one is what replaces the single-lot assumption, so an unsampled
  sub-lot is a finding rather than a rounding detail.
- Date codes carry two digits of year. A population mixing nineties and
  noughties codes has no orderable span, which is an input to reject
  rather than an ordering to guess.

## Workflow

1. Validate every unit: a non-empty identifier, a wafer lot, an assembly
   lot, a manufacturing site and a four-digit date code. A blank field
   or a duplicate identifier is an input error.
2. Reject a population whose two-digit years straddle a century
   rollover; the span cannot be ordered from the codes alone.
3. Group the units on the traceability tuple. Each distinct tuple is a
   sub-lot; record which identifiers fall under each.
4. Take the date-code span in whole weeks between the oldest and newest
   unit and compare it with the span the sampling policy admits.
5. Size the required sample from the lot size by exact ceiling division
   of the declared ratio, then apply the floor, the cap, and the lot
   size itself as the last bound.
6. Map the already-drawn specimens onto their sub-lots. Refuse a
   specimen that is not part of the population and a specimen drawn
   twice; count what landed in each sub-lot and list those that got
   none.
7. Return one verdict in precedence order: date-code span exceeded,
   several sub-lots where only one was admitted, a sample that is
   undersized or leaves a sub-lot untouched, otherwise a uniform lot the
   specimens may be drawn from. Report the span, the sub-lot count, the
   share sitting in the largest sub-lot, the required and actual sample
   sizes, and every finding.

## Pitfalls

- Reading one part number as one lot. The part number is what was
  ordered; the traceability tuple is what arrived. A delivery can carry
  one number and four sub-lots, and testing five specimens from the
  biggest of them leaves three sub-lots untested.
- Treating the date-code span as cosmetic once the traceability tuples
  agree. The two axes are independent: a single assembly lot drawn from
  wafers started months apart still spans process drift the lot test was
  supposed to bound.
- Letting a unit with a blank wafer lot ride along because the rest of
  the population is uniform. The unit cannot be placed, so the sample
  either misses it or misrepresents it; the assessment stops instead.
- Computing the sample size as a percentage in floating point. A lot of
  exactly two hundred against a tenth lands on the boundary, and the
  rounding of that boundary is the one number reviewers compare between
  two sites.
- Reporting a pass because the sample size was met. Size and coverage
  are different questions: the required count can be drawn entirely from
  one sub-lot, which satisfies arithmetic and answers nothing about the
  rest of the delivery.
- Averaging the sub-lots into a share and calling a high share uniform.
  The share is a description of the delivery, not a verdict; one part
  from an undeclared run is still an undeclared run.

## Behavior contract (gate 3)

The unit validation, century-rollover refusal, traceability grouping,
date-code span, integer sample sizing, coverage mapping and verdict
precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_lot_homogeneity.py against
scripts/q6013_class_1_lot_homogeneity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_lot_homogeneity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
