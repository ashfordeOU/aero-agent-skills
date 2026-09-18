---
name: q6005-construction-analysis-of-sample-units
description: "Evaluate the destructive teardown of sample units drawn from a supplier's production run and decide whether the delivered build matches what was declared, under ECSS-Q-ST-60-05 clause 6.3.2. Use when a category two validation needs its construction evidence graded: size the unit set from the product family, lots and variants, reject a unit built on an engineering bench, test whether the set spans the lots and build standards it claims for, grade each teardown step, group every deviation by what it touches and how widely it appears, and return the build-conformity index with one verdict. Trigger: ecss, q-st-60-05, category-two-construction-analysis, sample-unit-teardown, sample-unit-representativeness, internal-construction-examination, build-standard-deviation, teardown-step-coverage, construction-analysis-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-construction-analysis-of-sample-units, category-two-construction-analysis, sample-unit-teardown, sample-unit-representativeness, internal-construction-examination, build-standard-deviation, construction-analysis-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Construction Analysis of Sample Units (space-systems/ecss/q6005-construction-analysis-of-sample-units)

Use when the task is clause 6.3.2 of ECSS-Q-ST-60-05: the teardown of
representative units inside a category two validation — the element that looks
at how the product is actually built, rather than at how it performs or at how
the supplier says the line is run.

## Domain quick reference

- The units are destroyed to be read, so where they came from is part of the
  evidence. A unit built on an engineering bench is not a unit off the line
  the validation is about; it cannot carry the argument however carefully it
  was torn down, and it does not cover the lot it was labelled with either.
- The unit count comes from three directions at once: a floor for the product
  family, one unit per declared production lot and one unit per declared
  design variant. The largest governs, so a family floor of three does not
  cover five lots.
- Count and coverage are separate questions. A set can be exactly the right
  size and still leave a declared lot, variant or build standard with no unit
  speaking for it, and the analysis then has nothing to say about them.
- Five steps are what the teardown exists for: opening the package, the
  internal visual examination, the cross-section, the attach-integrity
  examination and the interconnect examination. Skipping one makes the
  analysis incomplete rather than merely weaker, because no other step answers
  the question it answers.
- A deviation is graded from what it touches and how widely it appears across
  the set, never from how bad it looked on the bench. Construction outside the
  declared build standard is critical on a single unit. An attach or bond
  integrity deviation is critical once it spans the set and major below that.
  Dimensional or cosmetic workmanship on a minority of units is minor.
- The build-conformity index ranks what is outstanding. A critical deviation,
  an inadmissible unit source or a missing mandatory step decides the outcome
  on its own, at any index.

## Workflow

1. Name the product and its family, and collect the production lots, design
   variants and build standards the teardown is meant to speak for.
2. Validate the unit set: a unit identifier appears once, each unit names its
   lot, variant, build standard and origin, and an unknown origin is an input
   error rather than a unit quietly admitted.
3. Separate the units whose origin cannot carry the analysis, and keep them
   out of both the count and the coverage test.
4. Compute the required unit count from the family floor, the declared lots
   and the declared variants, and compare it with the admissible set actually
   torn down.
5. Test coverage separately, naming every declared lot, variant and build
   standard no admissible unit represents.
6. Grade every teardown step against the full step set, so a step nobody
   mentioned is graded as not performed, and mark the mandatory ones missing.
7. Group each observed deviation into its severity category from the
   construction it touches and the share of units it appears on, absorbing the
   set-wide comparison with a named tolerance.
8. Take the weighted credit over total weight as the build-conformity index
   and name the verdict — incomplete while the set, the origins or the
   mandatory steps are short, build not confirmed on a critical deviation or a
   low index, confirmed with open actions when findings remain, confirmed only
   when none do.

## Pitfalls

- Tearing down whatever units the supplier had to hand. A bench build is the
  easiest unit to release and the one that proves least; the set has to come
  off the run the validation is about.
- Meeting the family floor and calling the set representative. Three units
  across five production lots is the right count for the wrong question.
- Letting a bench unit cover a declared lot because it carries the label. The
  label is not the origin, and the lot stays unrepresented.
- Grading a deviation by how alarming the photograph is. Severity comes from
  what it touches and how far it spreads; a faint feature on every unit is a
  build feature, a dramatic one on a single unit may be handling.
- Reading construction that differs from the declared build standard as a
  documentation issue. It means the delivered article is not the article
  described, which is the failure the teardown exists to catch.
- Letting a high index carry an analysis that never opened a package. The
  index averages; the mandatory steps do not.
- Re-using an earlier teardown on a product whose line or build standard has
  since moved. The construction is exactly what moves when the line moves.

## Behavior contract (gate 3)

The unit sizing, unit-origin admissibility, coverage test, teardown-step
grading, mandatory-step rule, deviation severity grouping, build-conformity
index and analysis verdict are exercised by the gate 3 contract test:
scripts/test_q6005_construction_analysis_of_sample_units.py against
scripts/q6005_construction_analysis_of_sample_units_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_construction_analysis_of_sample_units.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
