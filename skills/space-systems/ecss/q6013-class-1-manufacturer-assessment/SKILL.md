---
name: q6013-class-1-manufacturer-assessment
description: "Use when an audit report, questionnaire return or certificate pack has to decide a manufacturer. Assess the quality system of a commercial part manufacturer before a Class 1 acceptance under clause 4.2.3.2 of ECSS-Q-ST-60-13C: rate each dimension, from quality management, process-change notification and wafer-to-assembly lot traceability through reliability monitoring, failure analysis, discontinuance notice and subcontracted assembly control, discount every rating by the confidence its evidence basis earns, apply the veto rules that sink an assessment whatever it scored, check the evidence age, and return a weighted score with the actions owed. Trigger: ecss, q-st-60-13c, q6013-class-1-manufacturer-assessment, manufacturer-quality-system-dimension, assessment-evidence-basis-tier, manufacturer-assessment-verdict, process-change-notification-commitment."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-1-manufacturer-assessment, manufacturer-quality-system-dimension, assessment-evidence-basis-tier, manufacturer-assessment-verdict, process-change-notification-commitment, wafer-and-assembly-lot-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 1 Manufacturer Assessment (space-systems/ecss/q6013-class-1-manufacturer-assessment)

Use when the task is clause 4.2.3.2 of ECSS-Q-ST-60-13C: the manufacturer
behind a commercial part, and the quality system behind the product, have to
be assessed before the part is accepted for the highest assurance class. This
leaf grades the assessment and names what the outcome is.

## Domain quick reference

- The assessment is scored over a fixed dimension set, each weighted by how
  much of the risk it holds down. The weighting exists to rank repairs, not to
  let a strong area pay for a weak one.
- Three dimensions are load-bearing and hold a veto: the quality management
  system, the commitment to notify process changes, and traceability back to
  the wafer and the assembly lot. Lose one and nothing else in the assessment
  survives it, because those three are what make every later control -- lot
  acceptance, alerts, failure analysis -- mean anything at all.
- A dimension carries two independent facts, and mixing them is the usual
  error. How well it was rated is one; what the rating was based on is the
  other. An on-site audit carries full confidence, a remote audit a little
  less, a third-party certificate less again, a self-declared questionnaire
  half, and an unevidenced claim nothing. The rating is discounted by that
  confidence, so a perfect questionnaire is worth half a perfect audit and is
  never recorded as the same result.
- A veto dimension is also breached when its evidence basis sits under the
  floor, whatever the rating says. Believing a self-declaration about lot
  traceability is precisely the failure the floor exists to stop.
- Evidence ages. Past its validity period the assessment cannot be accepted
  outright however it scored, and the best outcome left is an acceptance
  carrying actions.
- A dimension nobody mentioned is unevidenced, not excused. The full dimension
  set is graded every time, so a thin submission cannot shrink the assessment
  it is measured against.

## Workflow

1. Name the manufacturer, collect a rating and an evidence basis for each
   dimension, and record how old the evidence is.
2. Reject the submission before grading when a dimension, a rating or an
   evidence basis is unrecognised, or when a dimension is declared twice.
3. Expand to the full dimension set, grading anything unmentioned as
   unevidenced.
4. Discount every rating by the confidence of its evidence basis to get the
   credit, and the weighted shortfall from it.
5. Apply the veto rules: a load-bearing dimension not met, or one evidenced
   below the floor, is a breach, and the breaches are named individually.
6. Take the weighted credit over the total weight as the score, and test the
   evidence age against its validity period.
7. Name the outcome from the score, the veto state and the evidence age --
   rejected on any breach or a score under the lower threshold, actions
   required in the band between, accepted only above the upper threshold with
   evidence still in validity -- and return the actions ranked by weighted
   shortfall.

## Pitfalls

- Recording a rating without its evidence basis, so a questionnaire return and
  an audit finding land in the same column and score the same.
- Letting a high overall score carry a manufacturer past a veto dimension. The
  veto is not a weight; no score reaches around it.
- Accepting a quality certificate as evidence of lot traceability. The
  certificate covers the system, not the route from a delivered part back to
  its wafer and assembly lot.
- Treating an old audit as evidence forever. The validity period exists
  because the line, the site and the subcontractors move.
- Grading only the dimensions the submission chose to answer, so the
  unanswered ones never surface as unevidenced.
- Closing an assessment on the verdict alone and losing the ranked actions,
  which are the only part of the output that says what to do next.
- Assuming a subcontracted assembly site inherits the quality system of the
  manufacturer whose name is on the part.

## Behavior contract (gate 3)

The dimension weighting, rating scores, evidence confidence discount, veto
rules and evidence floor, weighted score, validity check, outcome thresholds
and ranked actions are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_manufacturer_assessment.py against
scripts/q6013_class_1_manufacturer_assessment_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_1_manufacturer_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
