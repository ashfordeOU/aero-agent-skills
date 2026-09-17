---
name: q60-class-2-constructional-analysis
description: "Evaluate a constructional analysis carried out on Class 2 evaluation samples under ECSS-Q-ST-60C clause 5.2.3.3: size the destructive sample set from the part family and the declared procurement lots, confirm the sectioned samples actually reach every declared lot and date code, keep an unexecuted mandatory step apart from the conformance index instead of folding it in, weigh each anomaly by the internal barrier it sits on and how far it spreads through the set, and treat construction differing from the declared build as conclusive. Use when cross-section and internal-inspection results have to become one construction verdict. Trigger: ecss, q-st-60c-clause-5-2-3-3, class-2-constructional-analysis, class-2-evaluation-sample-representativeness, class-2-metallographic-cross-section, class-2-internal-visual-inspection, class-2-construction-anomaly-severity, class-2-construction-verdict."
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
  tags: [ecss, q-st-60c-class-2-eee-scope, q-st-60c, q60-class-2-constructional-analysis, q-st-60c-clause-5-2-3-3, class-2-evaluation-sample-representativeness, class-2-metallographic-cross-section, class-2-internal-visual-inspection, class-2-construction-anomaly-severity, class-2-construction-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Constructional Analysis (space-systems/ecss/q60-class-2-constructional-analysis)

Use when the task is clause 5.2.3.3 of ECSS-Q-ST-60C: the cross-sectioning and
internal inspection of representative samples inside a Class 2 component
evaluation — the part of the campaign that looks at how the device is actually
built rather than at how it performs.

## Domain quick reference

- The analysis destroys what it looks at. Every sample sectioned is a sample
  nobody can inspect again, so the sample set is the whole argument and a
  conclusion drawn from a set that never reached a declared lot is a
  conclusion about the samples rather than about the part.
- Sample size comes from two directions at once: a floor for the part family,
  and one sample for every declared procurement lot. The larger of the two
  governs, so a family floor of three does not cover five procurement lots.
- Reach is a separate question from count. A set can be exactly the right size
  and still leave a declared date code unsectioned, and the analysis then has
  nothing to say about the material shipped under it. Each unreached lot and
  each unreached date code is a separate repair and is named separately.
- A step that never ran is not a step that found nothing. Mandatory steps are
  tracked apart from the conformance index, because an index computed over
  what happened to be executed reads well precisely when the missing step was
  the one that mattered.
- An anomaly is weighed by the internal barrier it sits on and by how far it
  spreads through the set, not by how alarming the photograph is. A hermetic
  seal and a termination finish are not the same finding at the same extent.
- A single occurrence still carries a substantial share of its barrier's
  weight. The set is small and nothing can be sectioned twice, so one
  observation is evidence about the population rather than an outlier.
- Construction differing from what was declared is the failure the analysis
  exists to catch. It is conclusive on its own, whatever the conformance index
  or the anomaly grades say.
- A major finding is conclusive even on an incomplete analysis. Incompleteness
  decides only a set that found nothing disqualifying.

## Workflow

1. Name the part family and every declared procurement lot and date code. An
   unrecognised family is an input error, not a default.
2. Size the requirement: the family floor against one sample per declared lot,
   larger wins. Repeated lot names do not inflate it.
3. Read the sectioned set and check its reach against the declared lots and
   date codes, collecting every gap rather than the first one.
4. Record each inspection step as executed or not and as conforming or not,
   and refuse a record that claims conformance without execution.
5. Separate the mandatory steps that never ran from the conformance index over
   the steps that did.
6. Weigh each anomaly from its barrier and its incidence across the sectioned
   set, then group it as major, minor or an observation, absorbing a severity
   that lands on a bound with a named tolerance rather than by moving it.
7. Read the declaration check on every sample before anything else can accept
   the construction.
8. Return one verdict with the findings that produced it: rejected on a major
   anomaly or a declaration mismatch, incomplete on a short or unreaching set
   or a skipped mandatory step, accepted with a limitation on minor anomalies,
   accepted otherwise.

## Pitfalls

- Meeting the family floor and calling the set representative although five
  procurement lots were declared. The floor is a minimum, not the answer.
- Sectioning the convenient lot and drawing a lot-wide conclusion from it.
- Reporting the first population gap and stopping. A missing lot and a missing
  date code are different repairs and a plan needs both.
- Folding a skipped mandatory step into the conformance index. A high index
  over four executed steps says nothing about the cross-section that never ran.
- Grading an anomaly by how alarming the image is rather than by what it
  touches and how widely it appears.
- Dismissing a single occurrence as an outlier. In a destructive set of three
  it is a third of everything anybody will ever see.
- Reading construction that differs from the declared build as a documentation
  issue to be corrected later. It is the finding the analysis exists for.
- Letting an incomplete analysis suppress a major anomaly it did find. The
  anomaly stands; the incompleteness is a second, separate finding.
- Re-using an earlier analysis on a part whose assembly site has since moved.

## Behavior contract (gate 3)

The sample sizing rule, population reach check, mandatory-step separation,
conformance index, barrier-and-incidence anomaly severity, declaration check
and verdict ordering are exercised by the gate 3 contract test:
scripts/test_q60_class_2_constructional_analysis.py against
scripts/q60_class_2_constructional_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_constructional_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
