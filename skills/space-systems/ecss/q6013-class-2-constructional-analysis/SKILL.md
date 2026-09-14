---
name: q6013-class-2-constructional-analysis
description: "Assess the constructional analysis of a commercial EEE part at the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.2.3.3: confirm the sample was drawn from the lot being bought, drop the steps the package gives nothing to measure, grade every applicable inspection step for sample size and for what it found, score each observation by severity against the weight of the step that found it, hold the structural steps no analysis may skip, sum a construction risk index, and return the weaknesses that drive a mitigation or a rejection with one verdict. Use when an internal-construction report decides whether a commercial part type may be baselined. Trigger: ecss, q-st-60-13c-clause-5-2-3-3, class-two-constructional-analysis, commercial-part-internal-construction, constructional-analysis-lot-representativeness, construction-weakness-severity-index, structural-inspection-step-coverage."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-2-constructional-analysis, class-two-constructional-analysis, commercial-part-internal-construction, constructional-analysis-lot-representativeness, construction-weakness-severity-index, structural-inspection-step-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Constructional Analysis (space-systems/ecss/q6013-class-2-constructional-analysis)

Use when the task is clause 5.2.3.3 of ECSS-Q-ST-60-13C at the intermediate
assurance class: a commercial part has been opened up and looked at from the
outside in, and the question is whether what the inspection found leaves the
part type usable, usable once mitigated, or not usable at all.

## Domain quick reference

- The analysis is a set of inspection steps, and each step supplies a share
  of the internal picture. The weights are what let an analysis with one
  finding be ranked against an analysis with three.
- Three steps are structural. The internal visual inspection, the die
  metallisation inspection and the wire bond integrity test each reach a
  failure mode nothing else in the set reaches, so an analysis that skipped
  one is incomplete however clean the rest came back.
- Some steps depend on the package. A hermeticity test and an internal water
  vapour measurement have nothing to measure on a plastic-encapsulated part,
  so for that package they leave the set rather than counting as gaps.
- Every step owes a sample, and the sample owes a size. A step run on fewer
  parts than it requires has been run on too little to be representative; it
  is reported as under-sampled, not carried forward as evidence.
- The sample has to come from the lot the programme is buying. A part from
  another date code describes a construction the programme is not receiving,
  and that is the quietest way an analysis is made to say nothing at all.
- Observations are grouped by severity, and the severity is scored against
  the weight of the step that raised it. The weighted sum over the applicable
  weight is a construction risk index between zero and one, read against two
  bounds: acceptable, acceptable once mitigated, or rejected.
- The index is a summary, and a summary can average a showstopper away. A
  single disqualifying defect rejects the part type outright, and a named
  construction weakness always owes a mitigation even when the index is low.

## Workflow

1. Name the part type and the package, and read the date code of the analysis
   sample against the date code of the procurement lot.
2. Collect what each inspection step declares: whether it was performed, the
   sample it was performed on, and the severity of what it found.
3. Reject the report before grading when a step name, a package type or a
   severity is unrecognised, when a step is declared twice, or when a step
   that was not performed still carries a sample or an observation.
4. Expand the report to the full step set, mark each step applicable or not
   from the package, and grade anything applicable but not mentioned as not
   performed.
5. Grade each applicable step: under-sampled, skipped, or carrying an
   observation, and name the structural steps among them separately.
6. Score every observation by severity, weight it by its step, and take the
   weighted sum over the applicable weight as the construction risk index.
7. Rank the weaknesses heaviest first so the repair list leads with the step
   that matters most.
8. Name the verdict -- incomplete while a structural step is missing or the
   sample does not represent the lot, rejected on a disqualifying defect or
   an index past the upper bound, mitigated on a weakness or a middling
   index, acceptable only when none of that is true.

## Pitfalls

- Reading the risk index first and letting a low number close out a part that
  carries a disqualifying defect on one step.
- Counting a hermeticity result on a plastic-encapsulated part as a gap, or
  as a pass. The step had nothing to measure and belongs outside the set.
- Accepting a structural step run on a single part because the result was
  clean. One sample shows one construction, not the lot's.
- Taking an analysis performed on a sample from an earlier date code as
  covering the parts on order. Commercial construction moves between lots and
  nothing on the datasheet moves with it.
- Treating a step that was never mentioned as not applicable. A step nobody
  wrote down was not performed.
- Closing out a construction weakness with a note instead of a mitigation
  because the index came back inside the acceptable bound.
- Grading only what the decapsulation showed and skipping the external and
  radiographic steps that name where to look before the part is opened.

## Behavior contract (gate 3)

The step weighting, package applicability, sample size requirement, lot
representativeness, severity scoring, construction risk index, index bounds,
structural step completeness, weakness ranking and analysis verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_2_constructional_analysis.py against
scripts/q6013_class_2_constructional_analysis_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q6013_class_2_constructional_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
