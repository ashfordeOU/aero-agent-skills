---
name: e20-electromagnetic-effects-verification-plan
description: "Use when assess whether a verification plan closes every electromagnetic effects requirement the way the ECSS-E-ST-20C Annex B data-requirement expects: categorize each requirement by kind (radiated-emission, conducted-susceptibility, electrostatic-discharge, electrical-bonding-resistance, grounding-architecture, magnetic-moment-limit), check the assigned method -- verification-by-test, verification-by-analysis, verification-by-similarity, verification-by-review-of-design, verification-by-inspection -- can close that kind and names the evidence it needs, hold each activity at or above the requirement's integration level, and sum the declared coverage shares to a full requirement. Trigger: ecss, e-st-20-electrical-scope, e20-electromagnetic-effects-verification-plan, verification-method-admissibility, verification-coverage-share, integration-level-adequacy, electromagnetic-effects-requirement, method-evidence-record."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electromagnetic-effects-verification-plan, verification-method-admissibility, verification-coverage-share, integration-level-adequacy, electromagnetic-effects-requirement, method-evidence-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Electromagnetic Effects Verification Plan (space-systems/ecss/e20-electromagnetic-effects-verification-plan)

Use when the task is the content of the verification plan described by the
ECSS-E-ST-20C Annex B data-requirement -- the approach the programme takes to
the electromagnetic effects requirements, the method chosen for each one, the
integration level the method runs at, and the share of the requirement each
planned activity actually closes. The check is on the plan, before the
activities run; the results belong to the verification report.

## Domain quick reference

- Four sections make up the plan: the verification-approach-narrative, the
  requirement-to-activity-matrix, the method-justification-record and the
  facility-and-configuration-declaration. A section present as a heading but
  empty counts as undeclared -- most often the facility declaration, which is
  what makes a planned activity schedulable rather than aspirational.
- Each requirement carries a kind, and the kind constrains the admissible
  methods. A field quantity that only exists once the item is powered and
  radiating -- radiated-emission, radiated-susceptibility, conducted-emission,
  conducted-susceptibility, lightning-induced-transient -- cannot be closed by
  reading a drawing, so verification-by-review-of-design is inadmissible for
  it. A resistance across a bonding strap or the topology of a
  grounding-architecture can be closed by verification-by-inspection or
  verification-by-review-of-design, because the property is present in the
  built article whether or not it is powered.
- A method is only planned once it names the evidence it depends on:
  verification-by-test names a facility and a configuration,
  verification-by-analysis names its model, verification-by-review-of-design
  names the design document, verification-by-similarity names the heritage
  item and the delta argument against it, verification-by-inspection names the
  acceptance criterion. A method with no evidence field is an intention, not
  an activity.
- Verification-by-analysis of a radiated or lightning-coupled quantity carries
  an extra condition: the model has to be correlated against measured data.
  An uncorrelated field-solver run is a prediction, and closing a requirement
  on it transfers the whole modelling uncertainty into the flight article.
- Activities run at an integration level -- equipment-level, subsystem-level
  or system-level. An activity closes a requirement when it runs at that
  requirement's level or above; a system-level requirement closed by an
  equipment-level activity leaves every interaction between units unverified.
- A requirement may be split across several activities, each declaring the
  share it closes. The shares have to reach the whole requirement; a set that
  lands short leaves a deficit, and a set that overshoots signals double
  counting between two activities that verify the same thing.

## Workflow

1. Resolve the declared plan sections and list the ones that are absent or
   empty before looking at a single requirement.
2. For each requirement, resolve its kind and its integration level, then
   normalise every planned activity: identifier, method, level and the
   coverage share it declares. Reject a share outside the open-to-one range
   and a repeated activity identifier within one requirement.
3. Check the method against the kind. An inadmissible method is a finding on
   its own and stops the evidence check for that activity -- there is no
   point auditing the evidence of a method that cannot close the requirement.
4. Check the evidence fields the admissible method needs, and add the
   correlation condition when an analysis is being used to close a radiated
   or lightning-coupled quantity.
5. Compare each activity's integration level against the requirement's and
   record an activity that sits below it.
6. Sum the declared shares per requirement. Absorb float representation error
   at a requirement that is exactly fully covered rather than demanding an
   extra activity, and flag a sum that overshoots as double counting.
7. Compute the share of requirements that are fully covered, compare it
   against the floor the programme declared, and summarise the method mix so
   the review can see how much of the plan rests on measurement rather than
   argument.
8. The plan is acceptable only when no requirement carries a finding, the
   coverage share reaches its floor, and every section is declared.

## Pitfalls

- Closing a radiated requirement by review-of-design because the layout
  "obviously complies". The quantity does not exist until the item is powered;
  the method cannot produce the evidence, and a table of methods with no
  admissibility rule makes that invisible.
- Accepting verification-by-similarity with a heritage item named but no
  delta argument. Similarity is an argument about the difference, so the
  heritage reference alone carries none of the burden.
- Closing a field-quantity requirement on an uncorrelated model. The analysis
  looks like coverage in the matrix while the modelling uncertainty has been
  moved, unmeasured, into the flight article.
- Verifying a system-level requirement at equipment-level and declaring the
  requirement closed. Everything the requirement exists to catch -- the
  coupling between units, the harness routing, the structure return path --
  lies outside that activity.
- Counting activities instead of coverage shares. Three activities against one
  requirement mean nothing until their declared shares reach the whole; a
  requirement can carry several activities and still be short.
- Reading a sum slightly above the whole as conservative. An overshoot means
  two activities claim the same part of the requirement, and the surplus
  hides that one of them is likely mis-scoped.

## Behavior contract (gate 3)

The plan-section check, activity normalisation, method-to-kind admissibility
rule, method-evidence and model-correlation conditions, integration-level
adequacy and coverage-share summation are exercised by the gate 3 contract
test: scripts/test_e20_electromagnetic_effects_verification_plan.py against
scripts/e20_electromagnetic_effects_verification_plan_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electromagnetic_effects_verification_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
