---
name: q6013-class-3-manufacturer-assessment
description: "Use when a questionnaire return, certificate pack or audit report has to decide a commercial manufacturer for lowest-assurance use. Assess the capability and quality controls of a commercial part manufacturer at the lowest assurance class under clause 6.2.3.2 of ECSS-Q-ST-60-13C: credit each control at the lower of its declared maturity and the ceiling its evidence basis supports, take the weakest core control as the capability level rather than an average, test that level against the class-3 floor, shorten the surveillance interval for every supporting control beneath it, and return the verdict with each action owed. Trigger: ecss, q-st-60-13c, q6013-class-3-manufacturer-assessment, manufacturer-capability-level, control-evidence-ceiling, class-3-capability-floor, manufacturer-surveillance-interval."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-3-manufacturer-assessment, manufacturer-capability-level, control-evidence-ceiling, class-3-capability-floor, manufacturer-surveillance-interval, date-code-lot-traceability-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 3 Manufacturer Assessment (space-systems/ecss/q6013-class-3-manufacturer-assessment)

Use when the task is clause 6.2.3.2 of ECSS-Q-ST-60-13C: the capability of a
commercial part manufacturer, and the quality controls standing behind the
product, have to be assessed before the part is used at the lowest assurance
class. This leaf grades the assessment and names what follows from it.

## Domain quick reference

- The lowest assurance class accepts a lighter assessment, not a blank one.
  The control set does not shrink; what the class moves is the level each
  control has to reach and the evidence that may stand behind it.
- Every control carries two independent facts, and collapsing them is the
  usual error. The declared maturity -- absent, informal, documented, or
  documented and audited -- is a claim. The evidence basis behind it is a
  ceiling on what may be credited: an on-site or remote audit supports the top
  of the ladder, a certificate or a questionnaire supports a documented
  control and no more, a catalogue statement supports almost nothing. The
  credited level is the lower of the two, and the gap is reported rather than
  quietly absorbed.
- The capability level is a minimum, not an average. Three core controls --
  the quality system, the commitment to notify process changes, and
  traceability back to a date-code lot -- are only as strong as the weakest of
  them, and the control that set the level is named so the repair has an
  address. An average would let a strong quality system pay for absent
  traceability, which is the trade the minimum exists to refuse.
- The supporting controls do not set the level, they set the cadence. Each one
  below the class floor pulls the next surveillance visit forward, so a
  manufacturer with weak outgoing inspection or no discontinuance notice is
  revisited sooner rather than marked down.
- Evidence ages against that interval. Past it the assessment carries actions
  however well it read, because the interval is the statement about how long
  the evidence was ever meant to hold.
- A control nobody mentioned is absent and unevidenced. The full control set
  is graded every time, so a thin submission cannot shrink the assessment it
  is measured against.

## Workflow

1. Name the manufacturer, collect a maturity and an evidence basis for each
   control, and record how old the evidence is.
2. Reject the submission before grading when a control, a maturity or an
   evidence basis is unrecognised, when a control is declared twice, or when
   the manufacturer identifier is blank.
3. Expand to the full control set, grading anything unmentioned as absent and
   unevidenced.
4. Credit each control at the lower of its declared maturity and its evidence
   ceiling, and raise a finding wherever the ceiling did the capping.
5. Take the minimum credited level across the core controls as the capability
   level and name the control that governs it.
6. Count the supporting controls below the class floor, shorten the
   surveillance interval by one step each, and hold the interval at its floor
   rather than letting it go to nothing.
7. Test the evidence age against that interval, then name the outcome --
   rejected below the capability floor, accepted with actions while any
   finding stands, accepted only when neither is true.

## Pitfalls

- Recording a maturity without its evidence basis, so a questionnaire return
  and an audit finding land in the same column and credit the same level.
- Averaging the controls into a score. The core group is a chain, and a
  capability level read off an average survives a missing link.
- Reading a shortened surveillance interval as a penalty. It is the mechanism
  that lets a weak supporting control be accepted at all, and skipping the
  earlier visit removes the only thing that made it acceptable.
- Accepting a quality certificate as evidence of lot traceability. The
  certificate describes the system; traceability is the route from a delivered
  part back to the date-code lot it came from.
- Treating an old audit as evidence forever. The interval exists because the
  line, the site and the subcontractors move underneath a part number that
  never changes.
- Grading only the controls the submission chose to answer, so the unanswered
  ones never surface as absent.
- Closing on the verdict alone and losing the governing control and the action
  list, which are the only parts of the output that say what to do next.

## Behavior contract (gate 3)

The control set, maturity ladder, evidence ceilings, credited level, core
minimum rule, class floor, supporting-shortfall count, surveillance interval
and evidence-age test are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_manufacturer_assessment.py against
scripts/q6013_class_3_manufacturer_assessment_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_manufacturer_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
