---
name: q60-class-3-constructional-analysis
description: "Assess a constructional analysis run on Class 3 evaluation samples under ECSS-Q-ST-60C clause 6.2.3.3: size the destructive sample set from the lot populations and the date codes the parts came from, compare each cross-section against the declared construction baseline attribute by attribute, diff the sections across date-code groups to catch a build that moved without a notified change, weigh every difference by criticality into a conformance index, and close with one verdict. Use when cross-section and internal inspection results decide whether a Class 3 part's construction is acceptable. Trigger: ecss, q-st-60c, q60-class-3-constructional-analysis, q60-c3-construction-baseline-diff, q60-c3-date-code-group-consistency, q60-c3-section-sample-plan, q60-c3-construction-conformance-index."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q-st-60c, q60-class-3-constructional-analysis, q60-c3-construction-baseline-diff, q60-c3-date-code-group-consistency, q60-c3-section-sample-plan, q60-c3-construction-attribute-criticality, q60-c3-construction-conformance-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Constructional Analysis (space-systems/ecss/q60-class-3-constructional-analysis)

Use when the task is clause 6.2.3.3 of ECSS-Q-ST-60C: the cross-sectioning and
internal inspection of representative samples inside a Class 3 evaluation —
the part of the campaign that looks at how the device is actually built rather
than at how it performs.

## Domain quick reference

- The analysis asks two questions, and the second is the one usually skipped.
  Does the construction found inside the package match what the supplier
  declared, and do sections from different date codes agree with each other.
- The second question is the one that catches a Class 3 part changing
  underneath a programme. A single date code sectioned ten times answers the
  first question beautifully and says nothing at all about the second.
- The analysis is destructive, so the sample set is the whole argument. It has
  to reach every date code in the procurement and total enough sections that
  one unlucky device is not the evidence, which is why the plan carries both a
  per-date-code minimum and a floor that grows with the population.
- Construction attributes do not fail alike. A different bond wire metal is a
  different part; a different lead finish is a purchasing note. Each attribute
  therefore carries a criticality, and the criticality carries a weight.
- A sectioned dimension is a measurement, not a nameplate, so numeric
  attributes agree inside a stated relative band. Material names agree only on
  the name, normalized for case and spacing.
- A baseline attribute no section ever reported is not a passing attribute.
  It leaves the analysis incomplete, and folding it in with the passes hides
  exactly the attribute nobody looked at.
- The conformance index is weighted, so it separates a stack of cosmetic notes
  from one finding that changes what the part is. Critical and major
  differences block on their own; minor ones accumulate against a floor.

## Workflow

1. Declare the construction baseline: the attributes the supplier says the
   part is built from. Reject an attribute outside the published set, because
   a free-text attribute cannot be weighed.
2. Declare the date-code groups with their lot populations and the number of
   samples sectioned from each.
3. Size the plan: a per-date-code minimum, a total floor that grows with the
   combined population, and never more sections than there are parts.
4. Grade coverage per date code and in total, keeping the two shortfalls
   apart — a lot never sectioned and a set that is merely thin are different
   repairs.
5. Compare each group's section against the baseline, attribute by attribute,
   using the relative band for dimensions and the normalized name for
   materials. Reject a section reporting an attribute the baseline never
   declared, since there is nothing to compare it to.
6. Diff the groups against each other and name every attribute that moved
   between date codes, with the pair of codes it moved between.
7. Weigh every difference into the conformance index and close with one
   verdict: conforms, incomplete where coverage or an attribute is missing, or
   deviation.

## Pitfalls

- Sectioning one date code deeply and calling the procurement covered. Depth
  answers the baseline question; only breadth answers the consistency one.
- Reporting a conformance index without the criticality weights. Six cosmetic
  notes and one wrong die attach are not the same result, and an unweighted
  count says they are.
- Comparing a sectioned dimension for exact equality. The measurement carries
  its own spread, so the comparison uses a stated relative band and absorbs a
  value landing exactly on the band edge rather than failing it.
- Treating a baseline attribute nobody sectioned as a pass. It is unexamined,
  and the analysis stays incomplete until a section reports it.
- Letting a section introduce an attribute the baseline never declared. There
  is no declared value to compare it with, so the input is rejected rather
  than silently graded against nothing.
- Reporting only the first attribute that differs between date codes. Each one
  names a separate change to chase with the supplier.
- Ranking an incomplete sample set above a deviation already found. A found
  deviation is a fact about the part; a thin sample set is a gap in the
  evidence, and the fact is reported first.

## Behavior contract (gate 3)

The attribute catalogue and criticality weights, material and dimensional
matching, sample plan sizing, per-group and total coverage, baseline
comparison, cross-date-code consistency, weighted conformance index and the
closing verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_constructional_analysis.py against
scripts/q60_class_3_constructional_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_constructional_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
