---
name: q7003-bath-control
description: "Monitor the chemical control and analysis schedule of a black-anodizing line under the ECSS-Q-ST-70-03C process-control clause. Use when a tank reading, an overdue titration or a proposed bath addition has to be turned into a disposition before parts are run: place every parameter in its control band or its reject band, drive the analysis schedule off elapsed time and processed area together and take whichever arrives first, size the addition from tank volume, shortfall and additive strength, size the dilution when a parameter has drifted high instead, and roll the worst tank up into one line disposition. Trigger: ecss, q-st-70-03-black-anodizing-scope, anodizing-bath-control-limits, bath-analysis-schedule-interval, bath-addition-mass-calculation, bath-dilution-make-up, tank-out-of-service-disposition."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-bath-control, anodizing-bath-control-limits, bath-analysis-schedule-interval, bath-addition-mass-calculation, bath-dilution-make-up, tank-out-of-service-disposition, processed-area-analysis-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Bath Control (space-systems/ecss/q7003-bath-control)

Use when the task is the process-control clause of ECSS-Q-ST-70-03C --
keeping every tank on a black-anodizing line inside the chemistry it
was qualified at, deciding when each one is analysed, and turning a
titration result into an addition, a dilution or a stop.

## Domain quick reference

- Every parameter carries two bands, not one. Inside the control band
  the tank runs. Between the control band and the reject band it runs
  after a correction, because the chemistry is recoverable. Outside
  the reject band the tank comes off line, because a part already run
  through it cannot be recovered by anything done downstream.
- The two bands have to nest, and the nominal has to sit inside the
  control band. A parameter record whose bands cross is not a strict
  control limit, it is a typing error, and it is rejected rather than
  interpreted.
- Analysis runs on two clocks at once. A tank ages while it works,
  through drag-out, drag-in and dissolved metal, and it also ages
  while it idles, through evaporation and carbonation. So the schedule
  carries an elapsed-time interval and a processed-area interval, and
  whichever arrives first makes the analysis due.
- An overdue analysis is not a small version of a due one. Past the
  grace the last reading no longer describes the tank at all, so the
  tank comes off line rather than being flagged, and the record says
  which of the two clocks drove it.
- A correction is a weighed quantity. For a parameter below nominal it
  follows from the tank volume, the shortfall and the strength of the
  material being added, so a half-strength additive is twice the
  weight. That is the number the operator needs, not the shortfall.
- A parameter that has drifted high cannot be added to. It is brought
  back by make-up volume, and the dilution follows from the same
  arithmetic run the other way, which is also why a tank near its
  freeboard has fewer options than its reading suggests.
- The line is only as controlled as its worst tank. A line disposition
  is the worst tank disposition, and reporting it any other way lets a
  single rejected tank hide behind five healthy ones.

## Workflow

1. Validate each parameter record and reject crossed bands or a
   nominal outside the control band rather than repairing them.
2. Place each measured value into in-control, adjustment-required or
   out-of-service, treating a value that lands exactly on a band edge
   as inside that band.
3. Size the correction each drifted parameter needs: an addition mass
   from volume, shortfall and additive strength when the value is low,
   a make-up volume when it is high.
4. Run the analysis schedule on both clocks, take the one further
   through its interval, and record which one drove the answer.
5. Fold a due analysis into an adjustment and an overdue one into an
   out-of-service, rather than letting a stale reading stand.
6. Take the worst parameter as the tank disposition and the worst tank
   as the line disposition, then report the corrections, the findings,
   the tanks off line and the tanks owing an analysis.

## Pitfalls

- Controlling to a single limit. A tank with one number on the sheet
  gives the operator no way to tell a bath that needs a top-up from a
  bath that has already made bad parts, so every drift becomes either
  an unnecessary stop or an undetected escape.
- Scheduling analysis by calendar alone. A tank that ran three shifts
  of heavy loads is chemically older than the calendar says, and the
  processed-area clock is the only one that sees it.
- Treating an overdue titration as paperwork. The tank has been run on
  an assumption since the due point, so the question is not when to
  analyse it but which parts were made while nobody knew.
- Reporting the shortfall instead of the addition. The operator adds a
  mass into a volume, and a shortfall quoted per litre has to be
  multiplied by the tank and divided by the additive strength before
  it means anything on the scale.
- Averaging the line. Five healthy tanks and one rejected one is a
  stopped line, not a mostly-good one, and any roll-up that does not
  take the worst tank hides exactly the tank that matters.

## Behavior contract (gate 3)

The band nesting, parameter disposition, addition and dilution
arithmetic, two-clock analysis schedule, overdue grace, tank roll-up
and line disposition are exercised by the gate 3 contract test:
scripts/test_q7003_bath_control.py against
scripts/q7003_bath_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7003_bath_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
