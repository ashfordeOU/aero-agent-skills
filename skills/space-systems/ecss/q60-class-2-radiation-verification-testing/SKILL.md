---
name: q60-class-2-radiation-verification-testing
description: "Verify that a radiation-sensitive Class 2 EEE part meets the environment its mission declared under ECSS-Q-ST-60C clause 5.3.8: credit each heritage irradiation record through the knockdown its similarity tier earns, take the best credited capability as a radiation design margin computed in exact rational arithmetic, and settle the part on heritage, on its own flight-lot irradiation, or against a destructive single event whose onset sits below the mission requirement. Use when existing radiation evidence has to become an accept, test or reject decision. Trigger: ecss, q-st-60c-clause-5-3-8, class-2-part-radiation-verification, class-2-heritage-similarity-tier-credit, class-2-radiation-design-margin, class-2-destructive-single-event-veto, class-2-latch-up-mitigation-credit."
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
  tags: [ecss, q-st-60c-eee-class-2-scope, q60-class-2-radiation-verification-testing, class-2-part-radiation-verification, class-2-heritage-similarity-tier-credit, class-2-radiation-design-margin, class-2-destructive-single-event-veto, class-2-latch-up-mitigation-credit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts -- Radiation Verification Testing (space-systems/ecss/q60-class-2-radiation-verification-testing)

Use when the task is radiation verification under ECSS-Q-ST-60C clause 5.3.8:
a part the project graded radiation sensitive has to be shown to survive the
environment the mission declared, and the question is whether evidence that
already exists carries it, whether the flight lot owes its own irradiation, or
whether nothing obtainable from the part could close the gap.

## Domain quick reference

- The grading decides which questions are asked at all. A part graded sensitive
  to total dose only is not held to a single event threshold, and a part graded
  sensitive to neither raises no test under this clause.
- Heritage is the Class 2 shape of this clause. Evidence that did not come from
  the flight lot is admissible, but it is worth less the further the material
  tested sits from the material flying, so every record is credited through a
  knockdown for its similarity tier before it is compared with anything.
- The tiers run from the flight lot itself, through the same diffusion run and
  the same technology family, down to the process node alone. A large dose
  demonstrated at a distant tier can still beat a small one at a close tier,
  and when two records credit the same dose the closer tier is the better
  evidence.
- The margin is a dose ratio, and dose ratios land on the required margin
  constantly. That is exactly where float arithmetic decides the same part
  differently on two machines, so the credit, the capability and the margin are
  all exact rational arithmetic here.
- A single event is a veto, not a term in the margin. A destructive event whose
  onset threshold sits below the mission requirement rejects the part however
  wide the total dose margin is.
- The one mitigation credit is narrow. A verified protection outside the die can
  contain latch-up; it cannot contain burnout or gate rupture, which destroy the
  die before anything outside it acts.
- Evidence from the flight lot that falls short is a different answer from
  distant evidence that falls short. The first is the part's own capability and
  irradiating more of it changes nothing; the second is only a weak proxy.

## Workflow

1. Take the category the project graded the part to, and run only the checks it
   calls for.
2. Credit every heritage record through its similarity tier, refusing a tier the
   credit table does not declare and a demonstrated dose that is not positive.
3. Keep the record with the highest credited capability, breaking a tie towards
   the closer tier rather than towards whichever was listed first.
4. Form the radiation design margin as credited capability over declared mission
   dose, in exact rational arithmetic, and compare it with the required margin.
5. Route the dose question: accepted on heritage when the margin is met; a
   rejection when the flight lot's own evidence falls short; otherwise the
   flight lot owes its own irradiation.
6. Take the single event data separately. Pass anything onsetting at or above
   the mission requirement, veto a destructive event below it, credit a verified
   mitigation against latch-up alone, and carry a non-destructive event below
   the requirement as a rate question for the design.
7. Settle the part on the worst route either question earned, and report the
   record, the tier and the margin that produced it.

## Pitfalls

- Crediting heritage at face value. A dose demonstrated on another diffusion run
  is evidence about that run, and using it undiscounted accepts a part on
  material that never flew.
- Computing the margin in floats. The ratio lands on the bound constantly, and
  the same part then accepts on one build machine and fails on the next.
- Folding a single event threshold into the dose margin. They are different
  failure mechanisms; a generous total dose result cannot buy off a latch-up
  that destroys the part on the first heavy ion above its onset.
- Crediting a mitigation against burnout or gate rupture. The protection acts
  outside the die and those mechanisms have already destroyed it.
- Crediting an unverified mitigation. A declared current limiter that nobody
  demonstrated is a plan, not evidence.
- Sending a part back for irradiation when it was the flight lot's own data that
  fell short. More irradiation of that lot cannot raise its capability, and
  reporting it as outstanding hides a part that has to be changed.
- Treating a part nobody graded sensitive as untested. The grading is the input
  to this clause, and this clause raises nothing without it.

## Behavior contract (gate 3)

The category grading, similarity-tier credit, best-record selection, the exact
radiation design margin, the destructive single event veto, the narrow latch-up
mitigation credit and the route precedence are exercised by the gate 3 contract
test:
scripts/test_q60_class_2_radiation_verification_testing.py against
scripts/q60_class_2_radiation_verification_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
