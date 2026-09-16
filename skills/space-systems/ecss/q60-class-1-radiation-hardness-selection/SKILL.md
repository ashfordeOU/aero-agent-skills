---
name: q60-class-1-radiation-hardness-selection
description: "Use when a Class 1 design has to show a part survives its radiation environment for the full mission. Verify that a Class 1 part's radiation tolerance covers the environment it will actually see across the whole declared mission lifetime under ECSS-Q-ST-60C clause 4.2.2.4: accumulate ionising dose and displacement damage phase by phase behind the design shielding, raise each by its radiation design margin, cut a rate-sensitive technology's capability when it was characterised at a high dose rate, grade single event mechanisms separately for destructive and recoverable consequences, then name the binding mechanism, the open evidence and one disposition. Trigger: ecss, q-st-60-eee-selection-scope, class-1-radiation-hardness-selection, mission-accumulated-total-ionising-dose, radiation-design-margin-uplift, enhanced-low-dose-rate-sensitivity-cut, destructive-single-event-screening, displacement-damage-fluence-margin."
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
  tags: [ecss, q-st-60-eee-selection-scope, q60-class-1-radiation-hardness-selection, class-1-radiation-tolerance-matching, mission-accumulated-total-ionising-dose, radiation-design-margin-uplift, enhanced-low-dose-rate-sensitivity-cut, destructive-single-event-screening, displacement-damage-fluence-margin, mission-lifetime-dose-accumulation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Radiation Hardness Selection (space-systems/ecss/q60-class-1-radiation-hardness-selection)

Use when the task is the radiation matching of ECSS-Q-ST-60C clause
4.2.2.4 -- deciding, for a Class 1 design, whether a candidate part's
tolerance covers the environment behind its shielding over the full
declared mission lifetime, and what each shortfall costs.

## Domain quick reference

- A Class 1 part is not selected against a radiation number in the
  abstract. It is selected against the environment it will see behind
  the shielding the design gives it, accumulated over the declared
  mission, then raised by a design margin that covers spread in the
  environment model, in the lot, and in the prediction itself.
- Three mechanisms are graded separately because they are bought off in
  different currencies: total ionising dose in krad(Si), displacement
  damage as an accumulated non-ionising fluence, and single event
  effects as a threshold linear energy transfer the environment either
  does or does not exceed.
- Lifetime enters twice. Once as duration, because a phase contributes
  its rate multiplied by its years, so a mission extension is a dose
  increase and not a schedule note. Once as rate sensitivity, because a
  technology susceptible to enhanced low dose rate effects and
  characterised at a high dose rate does not carry that number into a
  long mission.
- Single event effects split by consequence. A recoverable upset,
  transient or functional interrupt can be answered by mitigation in
  the design. A latch-up, burnout or gate rupture destroys the part, so
  no amount of redundancy or scrubbing buys it back.
- A datasheet silent on a mechanism is an open item, not an immune
  part. Absent evidence is reported as evidence incomplete, which is
  neither a pass nor a breach, and it binds before a thin margin does.
- The useful output names the binding mechanism -- the one with the
  least room -- because that is what a shielding change, a mission
  extension or a lot change will break first.

## Workflow

1. Declare the mission as phases, each with a duration and the dose and
   fluence rates behind the design shielding, plus the part's
   technology, its rated capabilities and the basis they were taken on.
2. Accumulate dose and fluence across the phases, and carry the summed
   duration as the declared lifetime.
3. Raise each accumulated environment by its radiation design margin to
   get the capability the part actually has to meet.
4. Cut the rated dose capability by the technology's low dose rate
   factor whenever it was characterised at a high dose rate; leave a
   capability already taken at a low dose rate whole.
5. Grade each mechanism. Treat a capability landing exactly on its
   requirement as on-limit and adequate, not as a breach.
6. Grade each single event mechanism against the environment threshold,
   crediting declared mitigation only for recoverable consequences.
7. Close with the binding mechanism, every open evidence item, and one
   disposition: adequate, mitigation required, evidence incomplete, or
   inadequate.

## Pitfalls

- Comparing the part's capability with the bare mission environment.
  The margin is the whole point of the clause, and a part that meets
  the unmargined number has no cover for model or lot spread at all.
- Treating a mission extension as a schedule change. Dose accumulates
  with duration, so a part selected for a short mission can be short on
  dose the moment the operational phase is lengthened.
- Carrying a high dose rate characterisation straight into a long slow
  mission on a rate-sensitive technology. The number was taken under
  conditions the mission will not reproduce, so it is cut before
  comparison rather than after a shortfall appears.
- Taking mitigation as credit against a destructive event. Scrubbing
  and redundancy recover a corrupted state; they do not recover a part
  that has burned out, so the destructive mechanisms are graded on the
  part alone.
- Reading a silent datasheet as an absent problem. A mechanism with no
  threshold in the data was not measured, so it is carried as open
  evidence rather than quietly passed.
- Comparing a capability with a requirement by bare arithmetic. The
  capability is carried through a product of factors and the
  requirement through a sum of phase contributions, so a part built to
  sit exactly on its requirement can land a few units in the last place
  below it; the comparison absorbs that representation error while the
  requirement stays untouched.

## Behavior contract (gate 3)

The policy validation, phase accumulation, mission duration, margin
uplift, low dose rate capability cut, dose and displacement grading,
destructive and recoverable single event grading, binding-mechanism
selection and overall disposition are exercised by the gate 3 contract
test: scripts/test_q60_class_1_radiation_hardness_selection.py against
scripts/q60_class_1_radiation_hardness_selection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_radiation_hardness_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
