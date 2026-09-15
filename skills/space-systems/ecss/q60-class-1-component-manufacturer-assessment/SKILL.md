---
name: q60-class-1-component-manufacturer-assessment
description: "Assess a part manufacturer against the European space component baseline for Class 1 use under ECSS-Q-ST-60C clause 4.2.3.2: weight each assessment criterion, derate its rating by the evidence source behind it, derate a stale audit down to the weakest source, grade the whole baseline so an unmentioned criterion counts as unassessed rather than excused, block approval on any baseline criterion that falls short whatever the rest of the index says, and return the capability index, the blocking items and one verdict. Use when an audit report, a questionnaire or a third-party assessment decides whether a supplier may deliver Class 1 parts. Trigger: ecss, q-st-60c, component-manufacturer-assessment, space-component-baseline-criteria, manufacturer-capability-index, manufacturer-audit-validity, class-1-supplier-approval."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60c, q60-class-1-component-manufacturer-assessment, component-manufacturer-assessment, space-component-baseline-criteria, manufacturer-capability-index, manufacturer-audit-validity, class-1-supplier-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Component Manufacturer Assessment (space-systems/ecss/q60-class-1-component-manufacturer-assessment)

Use when the task is clause 4.2.3.2 of ECSS-Q-ST-60C: putting the manufacturer
of a candidate part through an assessment against the European space component
baseline criteria, as the part of a Class 1 evaluation that is about the
factory rather than about the device.

## Domain quick reference

- The assessment is a set of criteria, each carrying a weight that says how
  much of the manufacturer's standing it supplies. Four of them are the
  baseline: the quality system, process control, traceability and lot
  identification, and the change-notification procedure. Nothing else in the
  assessment compensates for them.
- Each criterion carries two separate facts. The rating says what was found.
  The evidence source says how much that finding is worth — a statement on a
  questionnaire and an observation at an on-site audit are not the same
  observation, so the source derates the rating instead of being filed beside
  it for the reader to weigh.
- Evidence older than the audit validity period is derated to the weakest
  supported source, not discarded and not kept at face value. An audit
  describes a factory on the day it was run, and the factory keeps moving.
- The capability index is weighted effective rating over total weight. It
  ranks manufacturers; it never approves one. A blocking baseline criterion
  fails the assessment at any index, because the index is exactly the
  averaging the baseline exists to prevent.
- A criterion nobody assessed is not assessed, not excused. The assessment is
  graded against the full criteria set every time, so a short report cannot
  shrink the baseline it is measured against.
- Approval with open actions is its own outcome. A factory that clears the
  baseline while carrying observations is usable, and the observations travel
  with every lot it ships until they are closed.

## Workflow

1. Collect what the assessment declares for each criterion: the rating, the
   evidence source it rests on, and the age of that evidence.
2. Reject the declaration before grading when a criterion name, a rating or a
   source is unrecognised, when a criterion appears twice, or when a rating
   is claimed with no evidence source behind it.
3. Expand the declaration to the full criteria set, grading anything not
   mentioned as unassessed on no evidence.
4. Derate each source for validity, then take the effective rating as the
   rating value times the source factor.
5. Test every baseline criterion against the minimum effective rating and
   collect the ones that block, heaviest first.
6. Take the weighted effective rating over the total weight as the capability
   index, absorbing the approval comparison with a named tolerance rather
   than by moving the approval bound.
7. Name the verdict — not approved while anything blocks or the index is
   short, approved with open actions when findings remain, approved only when
   neither is true — and carry the findings and any reassessment with it.

## Pitfalls

- Reading the capability index as a pass mark. It is an average, and the
  baseline criteria exist precisely because averaging a weak quality system
  against strong failure analysis hides the thing that matters.
- Recording the evidence source as a note beside a rating instead of letting
  it derate the rating. A fully compliant answer on a questionnaire is not a
  fully compliant finding, and filing both flat leaves the reader to make the
  judgement the assessment was supposed to make.
- Accepting an audit report that is years old because nothing in it looks
  wrong. Validity is about the factory having moved, not about the report
  having errors.
- Grading only the criteria the report happened to cover, so a criterion
  nobody thought about never appears as unassessed.
- Treating a third-party assessment as equivalent to an own audit on a
  baseline criterion. It is worth something, and on the baseline it is not
  worth enough on its own.
- Closing an assessment as approved when observations are still open. Approved
  with open actions is a different state and the actions belong to the part.
- Reporting the first blocking criterion only. Each one names a separate
  corrective action and the supplier needs all of them at once.

## Behavior contract (gate 3)

The criterion weights, rating scale, evidence-source derating, audit validity,
baseline blocking rule, capability index and manufacturer verdict are
exercised by the gate 3 contract test:
scripts/test_q60_class_1_component_manufacturer_assessment.py against
scripts/q60_class_1_component_manufacturer_assessment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_component_manufacturer_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
