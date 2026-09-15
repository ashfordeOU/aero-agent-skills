---
name: q60-class-1-radiation-verification-testing
description: "Verify that a radiation-sensitive Class 1 EEE part meets its declared mission radiation environment under ECSS-Q-ST-60C clause 4.3.8. Use when deciding whether heritage evidence already carries the required margin or the flight lot owes its own irradiation, crediting the lowest failure-free dose of the sample by how many parts were actually irradiated, comparing the demonstrated radiation design margin with the required one, and judging single event threshold linear energy transfer against the mission requirement. Refuses an unlisted technology family, a sample too narrow to earn lot credit, and a destructive single event onset under the required level however wide the dose margin. Trigger: ecss, q-st-60c, class-1-part-radiation-verification-test, mission-declared-radiation-environment, class-1-radiation-design-margin, irradiated-lot-sample-credit, single-event-latch-up-veto, enhanced-low-dose-rate-sensitivity-test."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-radiation-verification-testing, class-1-part-radiation-verification-test, mission-declared-radiation-environment, class-1-radiation-design-margin, irradiated-lot-sample-credit, single-event-latch-up-veto]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Radiation Verification Testing (space-systems/ecss/q60-class-1-radiation-verification-testing)

Use when the task is radiation verification testing under ECSS-Q-ST-60C
clause 4.3.8 — showing that a part the project has graded
radiation-sensitive survives the environment the mission declared, with
enough margin left over, before it is allowed onto a Class 1 build.

## Domain quick reference

- Sensitivity is a **declared property of the technology family**, not a
  judgement made per part number at assessment time. A family the
  project register never listed is refused; guessing it from the nearest
  listed family is how a sensitive part reaches flight untested.
- A verification test is owed unless heritage evidence already carries
  the required margin over the mission dose. Absent heritage evidence
  the test is owed — silence is not a waiver, and a part with no
  radiation history is the case the clause exists for.
- The lot is credited with the **lowest** failure-free dose across the
  irradiated parts, never the mean and never the best one. A part that
  failed early is the part the flight lot may also contain.
- Sample width buys credit. A wide sample carries the dose it reached; a
  narrow one is derated because it evidences less of the lot, and below
  the minimum irradiated count it earns no credit at all and is refused
  rather than derated to something small.
- Total dose margin and single event response are **separate verdicts**.
  A threshold linear energy transfer comfortably above the requirement
  does not rescue a part whose latch-up, burnout or gate rupture onset
  sits below it: a destructive event is a veto, not a margin to trade.
- A bipolar family flown at a low mission dose rate degrades further
  than an accelerated irradiation shows. Where the mission rate is under
  the threshold, the accelerated result alone is incomplete evidence,
  not a pass with a caveat.

## Workflow

1. Resolve the sensitivity grade of the technology family from the
   project register; refuse an unlisted family.
2. Decide whether a part-level irradiation is owed: never for a low
   grade, always for a sensitive part with no heritage evidence,
   otherwise only when heritage falls short of the required margin.
3. Before reading any dose result, test whether a low dose rate
   irradiation is also owed and has been performed. A missing one stops
   the assessment at incomplete evidence.
4. Reduce the irradiated sample to a lot capability: take the lowest
   failure-free dose and apply the credit the sample size earns.
5. Judge the single event response against the mission requirement,
   treating any destructive onset below it as a veto.
6. Compare the demonstrated radiation design margin with the required
   one and report the capability shortfall in dose, not only as a ratio.
7. Return the disposition: no test required, evidence incomplete, failed
   on single event response, failed on total dose, or verification
   passed.

## Pitfalls

- Averaging the failure-free doses of the sample. The mean hides the
  weak part, and the weak part is what the lot credit is protecting
  against.
- Reading the dose margin first and the single event result afterwards.
  A destructive onset below the requirement cannot be argued against a
  wide dose margin, so it has to be tested before the margin is seen.
- Treating a wide upset threshold as immunity. Upsets and destructive
  events have different onsets; the first says nothing about the second.
- Accepting an accelerated irradiation for a bipolar part on a low dose
  rate mission. That is the one case where the accelerated result is
  optimistic rather than conservative.
- Derating a two-part sample instead of refusing it. A credit table that
  runs below its smallest entry invents evidence the irradiation never
  produced.
- Quoting the margin as a ratio and stopping. A shortfall expressed in
  dose is what tells the project how much more capability it has to buy.

## Behavior contract (gate 3)

The sensitivity register lookup, test-necessity decision, sample credit,
lot capability reduction, margin comparison, low dose rate obligation
and single event verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_radiation_verification_testing.py against
scripts/q60_class_1_radiation_verification_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
