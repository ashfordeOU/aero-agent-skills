---
name: q60-class-3-radiation-verification-testing
description: "Verify that a radiation-sensitive Class 3 EEE part meets the environment its mission declared under ECSS-Q-ST-60C clause 6.3.8: take the lot capability as a one-sided lower tolerance bound on an irradiated sample, read the tolerance factor from a project table the sample size has to be listed in, derate a bipolar or optocoupler capability resting on high-dose-rate data alone, compare the radiation design margin with the required one through a named tolerance, and let a destructive single event inside the mission environment end the part whatever the margin says. Use when Class 3 irradiation data has to become an accept, test or reject decision. Trigger: ecss, q-st-60c-clause-6-3-8, class-3-lot-radiation-capability, class-3-lower-tolerance-bound-dose, class-3-eldrs-dose-rate-derating, class-3-radiation-design-margin, class-3-destructive-single-event-veto."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-3-radiation-verification-testing, class-3-lot-radiation-capability, class-3-lower-tolerance-bound-dose, class-3-eldrs-dose-rate-derating, class-3-radiation-design-margin, class-3-destructive-single-event-veto]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Radiation Verification Testing (space-systems/ecss/q60-class-3-radiation-verification-testing)

Use when the task is the radiation verification of ECSS-Q-ST-60C clause 6.3.8 —
showing that a Class 3 part the project called radiation sensitive survives the
environment the mission declared, and deciding what to do when it does not.

## Domain quick reference

- Only the technologies the project declared **dose sensitive** owe a
  verification. Running one for a film resistor buys nothing; what it costs is
  attention, and the parts that genuinely owe a verification are the ones that
  lose it.
- A Class 3 verification rests on a **sample of the flight lot**, not on one
  piece. The capability carried forward is a one-sided lower tolerance bound —
  the sample mean less a tolerance factor times the sample spread — so two
  samples with the same mean and different spreads do not credit the same
  capability. The wide one gives ground, which is the point.
- The tolerance factor comes from a **project table keyed on sample size**. A
  size the table does not list is refused rather than interpolated between two
  neighbours; between two entries the table states no factor at all, and
  inventing one invents the acceptance criterion.
- Bipolar linear parts and optocouplers can fail at a **lower total dose when
  the dose arrives slowly**. Where only high-dose-rate data exists, the
  capability is derated before it is compared with anything — after the
  comparison is too late, because the comparison already passed.
- The margin comparison sits on a **named tolerance**. An exact equality at the
  bound is a representation question, not an engineering one, and the tolerance
  absorbs it. The required margin itself is never widened to make a case pass.
- A **destructive single event** whose onset sits at or below the mission
  threshold ends the part however good the dose margin looks. Total dose and
  single events are different failure mechanisms, and a margin on one cannot
  buy relief on the other.
- Mitigation is a **project permission plus a declaration**, both. A latch-up
  the project allows to be handled at circuit level still vetoes the part when
  no mitigation was actually declared for it.

## Workflow

1. Normalize the part technology and stop early when the project does not treat
   it as dose sensitive.
2. Settle the single event picture first, so a destructive veto is visible
   before any effort goes into the dose numbers.
3. Where no flight-lot irradiation data exists, route the part to its own
   irradiation — or to rejection when a destructive event already vetoed it.
4. Compute the sample mean and spread, read the tolerance factor off the table
   for that exact sample size, and form the lower tolerance bound.
5. Derate the bound where the technology is dose-rate sensitive and only
   high-dose-rate data exists, and record that derating as a finding.
6. Form the radiation design margin against the mission dose requirement and
   compare it with the required margin through the named tolerance.
7. Route the part: reject on a destructive veto, accept on a margin that holds,
   otherwise send it for its own flight-lot irradiation.

## Pitfalls

- Crediting the sample mean as the lot capability. Half the lot sits below the
  mean, and the tolerance bound is what keeps that half inside the argument.
- Interpolating a tolerance factor for a sample size the table skips. The table
  is the criterion; between two entries there is no criterion to interpolate.
- Comparing the margin before applying the dose-rate derating. The order is the
  whole safeguard, and a derating applied afterwards never changes a verdict
  already given.
- Letting a good dose margin outweigh a destructive single event. They are
  different mechanisms, and only one of them destroys the part on first
  occurrence.
- Crediting a mitigation the project never permitted, or permitting one that
  was never declared. Either half alone leaves the event unhandled.
- Widening the required margin to absorb an equality at the bound. The
  representation question is already handled inside the comparison; the
  engineering limit stays as the mission specified it.

## Behavior contract (gate 3)

The sensitivity screen, the tabulated tolerance factor, the lower tolerance
bound, the dose-rate derating, the margin comparison through its named
tolerance and the destructive single event veto are exercised by the gate 3
contract test: scripts/test_q60_class_3_radiation_verification_testing.py
against scripts/q60_class_3_radiation_verification_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_3_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
