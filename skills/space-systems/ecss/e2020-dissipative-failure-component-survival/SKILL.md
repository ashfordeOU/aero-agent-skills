---
name: e2020-dissipative-failure-component-survival
description: "Evaluate whether the parts around a current limiter survive a switch that fails dissipatively while nothing else removes it, under clause 5.2.14.1.1 of ECSS-E-ST-20-20C. Use when a limiter switch is stuck in its limitation region and the dissipation runs indefinitely into the board and the neighbouring components. Compute the steady dissipation from the drop and the limited current, raise every named part through its own thermal coupling, compare each against its derated rating, report the surviving and the exceeded parts with margins, and derive the dissipation each part could have taken. Trigger: ecss, e-st-20-20c, dissipative-switch-failure-survival, limiter-dissipative-failure-heating, surrounding-part-thermal-survival, uncleared-limiter-dissipation, dissipative-failure-allowable-power."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-dissipative-failure-component-survival, dissipative-switch-failure-survival, limiter-dissipative-failure-heating, surrounding-part-thermal-survival, uncleared-limiter-dissipation, dissipative-failure-allowable-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Dissipative Failure Component Survival (space-systems/ecss/e2020-dissipative-failure-component-survival)

Use when the task is clause 5.2.14.1.1 of ECSS-E-ST-20-20C: a current limiter
switch fails dissipatively, no other means removes the failure, and the parts
around that switch have to survive it. This leaf turns the uncleared case into
a steady-state thermal assessment, part by part.

## Domain quick reference

- A dissipative failure is the one that does not announce itself. The switch
  neither opens nor shorts; it sits in its limitation region holding the
  limited current with the bus drop across it, so the load still works and the
  only symptom is heat.
- The dissipation is the drop across the failed switch times the current it
  holds, and it is the drop under the fault that matters, not the millivolts
  the switch drops when it is healthy. A limiter that is barely warm in
  operation is a tens-of-watts heater in limitation.
- The clause's case is the uncleared one, so the assessment is a steady state
  rather than an energy pulse. There is no time at which it stops, which is
  why the answer is a temperature and not a joule count.
- Coupling is per part, not per board. Each neighbouring part sees its own
  rise per watt dissipated in the switch, set by its distance, the copper
  between them and the mounting, so the part that fails first is frequently
  not the closest one.
- The limit to compare against is the derated one. The parts programme
  withholds margin from the rated maximum, and a survival argument made
  against the catalogue number spends margin that was already allocated.
- Reporting the allowable dissipation turns a pass or fail into a design
  input. A part that could have taken forty watts beside a switch holding
  fifty-six names both the problem and the size of the fix.
- A clearing device does not move this case. If a fuse or an upstream
  protection is declared, the clause still asks what happens when nothing
  removes the failure, so the uncleared steady state is graded and the
  clearing path is reported alongside it.

## Workflow

1. Validate the case: a named switch, a positive drop and limited current, a
   physically possible reference temperature, and at least one named part
   with a positive coupling and a rated maximum.
2. Reject a part already at or above its derated limit at the reference
   temperature; the survival question is not answerable for it.
3. Compute the steady dissipation the failed switch holds.
4. Raise each part from the reference by its coupling times that dissipation
   and compare it against its rated maximum less its withheld margin.
5. Invert the same relation to get the dissipation each part could have taken
   and keep the smallest as the limiting figure.
6. Report per part: temperature, derated limit, margin and allowable power;
   then the surviving and exceeded lists, the worst part and the headroom
   ratio against the dissipation actually held.
7. Note any declared clearing path as outside the clause's case, and return
   compliant only when every named part stays at or under its own limit.

## Pitfalls

- Using the healthy on-state drop. The whole point of the failure mode is
  that the switch now stands off most of the bus, and an assessment built on
  the operational drop understates the dissipation by orders of magnitude.
- Treating the event as a transient. Nothing clears it, so there is no pulse
  width to integrate and no thermal mass to hide behind; the part either sits
  below its limit forever or it does not.
- Comparing against the rated maximum. The derated limit is the one the parts
  programme will hold the design to, and passing against the catalogue figure
  is a finding waiting for the review.
- Assessing only the switch itself. The clause is about what surrounds it —
  the board, the mounting, the neighbouring parts — and a switch rated to
  survive its own failure proves nothing about the capacitor beside it.
- Giving the whole board one coupling figure. Averaging the rises hides the
  one part that is thermally welded to the switch and reports a margin no
  single component actually has.
- Letting a declared fuse close the case. A clearing path is worth reporting,
  but the clause asks about the failure nothing removes, so it is a note
  beside the verdict and never a substitute for it.

## Behavior contract (gate 3)

The case validation, dissipation arithmetic, derated-limit computation,
per-part temperature rise, allowable-power inversion, on-the-bound survival
handling, worst-part and headroom reporting, clearing-path note and verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_dissipative_failure_component_survival.py against
scripts/e2020_dissipative_failure_component_survival_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_dissipative_failure_component_survival.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
