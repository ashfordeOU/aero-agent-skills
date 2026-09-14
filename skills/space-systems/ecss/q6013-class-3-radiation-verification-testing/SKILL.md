---
name: q6013-class-3-radiation-verification-testing
description: "Verify a sensitive lowest assurance commercial EEE part against its mission radiation environment under ECSS-Q-ST-60-13C clause 6.3.8: triage the part for sensitivity from its technology family and the mission dose, scale the required capability by the declared design margin and by the penalty the evidence tier carries, compare a tested or declared total dose capability against that requirement, refuse a destructive single-event waiver on a susceptible family whatever the dose margin holds, and return not sensitive, verified, lot test required, evidence insufficient or rejected. Use when thin radiation evidence has to become a verdict. Trigger: ecss, q-st-60-13c-clause-6-3-8, class-three-radiation-verification, radiation-sensitivity-triage, evidence-tier-dose-penalty, total-dose-capability-margin, destructive-single-event-refusal, class-three-radiation-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-radiation-verification-testing, class-three-radiation-verification, radiation-sensitivity-triage, evidence-tier-dose-penalty, total-dose-capability-margin, destructive-single-event-refusal, class-three-radiation-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Radiation Verification Testing (space-systems/ecss/q6013-class-3-radiation-verification-testing)

Use when the task is the clause 6.3.8 radiation verification of
ECSS-Q-ST-60-13C at the lowest assurance category: a commercial part may
be radiation sensitive, the evidence behind it is thinner than an
irradiation of the lot that will fly, and the question is whether that
evidence clears the mission or has to be replaced by a test.

## Domain quick reference

- Sensitivity is asked before capability. A part that is neither in the
  sensitive technology register nor exposed to a mission dose reaching
  the screening threshold owes nothing at this category, and the whole
  assessment stops there rather than manufacturing a requirement.
- There are two independent routes into sensitivity and either is
  enough. The register catches the families whose response moves at any
  dose; the threshold catches everything else once the orbit is harsh
  enough to matter.
- The requirement is the mission dose scaled twice. The design margin
  covers the spread within a lot and the uncertainty in the environment;
  the evidence penalty covers the distance between the part that was
  irradiated and the part that will fly.
- The penalty is the whole mechanism this category rests on. An
  irradiation of the flight lot carries none, a similar lot carries
  some, and a number off a manufacturer's page carries the most, because
  nobody in the project saw that measurement being made.
- Shortfall is not always rejection. Thin evidence falling short can be
  answered by irradiating the lot, which is a schedule and cost problem;
  a flight lot that was actually tested and still fell short is a part
  problem and no further test will move it.
- A single particle does not care about a dose margin. A family that can
  be destroyed outright is judged on its own threshold against the
  environment, and no total dose result buys past it.
- Absent destructive single-event data on a susceptible family is a
  refusal, not an open item. The failure it guards against is
  unrecoverable, so silence has to read as the worst case.

## Workflow

1. Triage sensitivity from the technology family and the mission dose
   against the screening threshold; close the assessment on a part that
   is neither.
2. Run the destructive single-event check on its own terms: register
   membership, data presence, then threshold against the environment,
   with an exact landing on the environment counted as cleared.
3. Refuse a part offering no radiation evidence at all before any
   arithmetic is attempted.
4. Scale the mission dose into the required capability with the declared
   design margin and the evidence tier penalty.
5. Compare the tested or declared capability against that requirement,
   counting a capability landing exactly on it as meeting it, and record
   the shortfall when it does not.
6. Return one verdict and every reason: the destructive check outranks
   the dose result, a met requirement verifies, a replaceable tier
   falling short calls for a lot test, and a flight-lot tier falling
   short rejects.

## Pitfalls

- Starting at the dose requirement and never asking whether the part is
  sensitive. A requirement invented for an insensitive part generates
  test cost and no information.
- Applying the design margin and forgetting the evidence penalty. The
  margin says nothing about how far the measured part sits from the one
  in the box, which is exactly what this category relaxes.
- Treating a manufacturer's declared figure as a test result. It is a
  number on a page, which is why it carries the largest penalty and why
  a shortfall against it means the lot has to be irradiated.
- Reading a healthy dose margin as a clean bill. A destructive
  single-event failure has no dose dependence, and the margin has no
  bearing on it.
- Leaving missing single-event data as an open item to close later. At
  this category the part flies as procured, so an open item is a
  decision to accept the failure.
- Relaxing the requirement so a capability sitting exactly on it passes.
  A value on its limit is inside it, and the representation error at
  that boundary is absorbed by the tolerance inside the comparison
  rather than by moving the requirement.

## Behavior contract (gate 3)

The sensitivity triage on both routes, the evidence tier penalties, the
required capability scaling, the total dose comparison at and around its
limit, the destructive single-event check including the missing-data
refusal, and the five verdicts are exercised by the gate 3 contract
test: scripts/test_q6013_class_3_radiation_verification_testing.py
against scripts/q6013_class_3_radiation_verification_testing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_3_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
