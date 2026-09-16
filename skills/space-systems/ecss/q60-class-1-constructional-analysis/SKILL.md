---
name: q60-class-1-constructional-analysis
description: "Use when cross-section and internal-inspection results decide whether a part's construction is acceptable. Evaluate a constructional analysis carried out on Class 1 evaluation samples under ECSS-Q-ST-60C clause 4.2.3.3: size the sample set from the part family and the declared diffusion and assembly lots, check that the cross-sectioned samples actually span the lots and date codes they claim to speak for, grade every internal inspection step and treat a skipped mandatory one as incomplete rather than merely weaker, group each observed anomaly by what it touches and how widely it appears, and return the conformance index with one verdict. Trigger: ecss, q-st-60c, class-1-constructional-analysis, evaluation-sample-representativeness, evaluation-metallographic-cross-section, class-1-internal-visual-inspection, construction-anomaly-severity, class-1-construction-verdict."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60c, q60-class-1-constructional-analysis, evaluation-sample-representativeness, evaluation-metallographic-cross-section, class-1-internal-visual-inspection, construction-anomaly-severity, class-1-construction-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Constructional Analysis (space-systems/ecss/q60-class-1-constructional-analysis)

Use when the task is clause 4.2.3.3 of ECSS-Q-ST-60C: the cross-sectioning and
internal inspection of representative samples inside a Class 1 evaluation —
the part of the campaign that looks at how the device is actually built rather
than at how it performs.

## Domain quick reference

- The analysis is destructive, so the sample set is the whole argument. Every
  sample consumed is a sample nobody can re-inspect, and a conclusion drawn
  from a set that never covered a declared lot is a conclusion about the
  samples rather than about the part.
- Sample size comes from two directions at once: a floor for the part family,
  and one sample for each declared diffusion lot and each declared assembly
  lot. The larger of the two governs, so a family floor of two does not cover
  five diffusion lots.
- Representativeness is a separate question from count. A set can be the right
  size and still leave a declared date code unrepresented, and the analysis
  then has nothing to say about the material shipped under it.
- Four steps are what the analysis exists for: the internal visual inspection,
  the metallographic cross-section, the die-attach examination and the
  interconnect examination. Skipping one makes the analysis incomplete, not
  merely weaker, because no other step answers the question it answers.
- An anomaly is grouped by what it touches and how widely it appears, never by
  how bad it looked down the microscope. Construction outside what the
  manufacturer declared is critical on a single sample. An interconnect
  integrity anomaly is critical once it spans the set and major below that.
  Workmanship on a minority of samples is minor.
- The conformance index ranks what is outstanding. A critical anomaly or a
  missing mandatory step decides the outcome on its own, at any index.

## Workflow

1. Name the part family and collect the declared diffusion lots, assembly lots
   and date codes the analysis is meant to speak for.
2. Validate the sample set: a sample identifier appears once, and each sample
   names the diffusion lot, assembly lot and date code it came from.
3. Compute the required sample count from the family floor and the declared
   lots, and compare it with the set actually sectioned.
4. Test coverage separately, naming every declared lot and date code no sample
   represents. Each one is a separate gap in the argument.
5. Grade every inspection step against the full step set, so a step nobody
   mentioned is graded as not performed, and mark the mandatory ones missing.
6. Group each observed anomaly into its severity category from the
   construction it touches and the share of samples it appears on, absorbing
   the lot-wide comparison with a named tolerance.
7. Take the weighted credit over the total weight as the conformance index and
   name the verdict — incomplete while the set or the mandatory steps are
   short, not acceptable on a critical anomaly or a low index, acceptable with
   open actions when findings remain, acceptable only when none do.

## Pitfalls

- Meeting the family floor and calling the set representative. Two samples out
  of five diffusion lots is the right count for the wrong question.
- Sectioning several samples from the convenient lot because they were the
  ones on the shelf. The set has to span the declared material, and a set
  drawn from one lot says nothing about the others.
- Grading an anomaly by how alarming the photograph is. Severity comes from
  what the anomaly touches and how far it spreads; a faint feature present on
  every sample is a construction feature, and a dramatic one on a single
  sample may be handling.
- Reading a construction that differs from the manufacturer's declaration as a
  minor documentation issue. It means the delivered article is not the article
  described, which is the failure the analysis exists to catch.
- Letting a high conformance index carry an analysis that never ran the
  cross-section. The index averages; the mandatory steps do not.
- Treating a date code gap as covered because the diffusion lot was sampled.
  They are separate declarations and each is reported on its own.
- Re-using an earlier analysis on a part that has since changed assembly site
  or lot. The construction is exactly what moves when the line moves.

## Behavior contract (gate 3)

The sample sizing, coverage test, inspection-step grading, mandatory-step
rule, anomaly severity grouping, conformance index and analysis verdict are
exercised by the gate 3 contract test:
scripts/test_q60_class_1_constructional_analysis.py against
scripts/q60_class_1_constructional_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_constructional_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
